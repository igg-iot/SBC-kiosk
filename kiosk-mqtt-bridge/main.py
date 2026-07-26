#!/usr/bin/env python3
import sys
import time
import subprocess
import paho.mqtt.client as mqtt
import multiprocessing

import config
import discovery
import hardware

def diagnostic_loop(broker, port, user, password, client_id, topic_prefix):
    """Executes in an isolated process to poll hardware without blocking the main event loop."""
    diag_client = mqtt.Client(client_id=f"{client_id}_diag")
    if user and password:
        diag_client.username_pw_set(user, password)
    
    try:
        diag_client.connect(broker, port, 60)
        diag_client.loop_start()
    except Exception as e:
        print(f"Diagnostic process failed to connect: {e}", file=sys.stderr)
        return

    try:
        while True:
            rssi = hardware.get_wifi_rssi()
            if rssi is not None:
                diag_client.publish(f"{topic_prefix}/wifi_rssi/state", str(rssi))
                
            mem = hardware.get_free_mem()
            if mem is not None:
                diag_client.publish(f"{topic_prefix}/free_mem/state", str(mem))
                
            temp = hardware.get_cpu_temp()
            if temp is not None:
                diag_client.publish(f"{topic_prefix}/cpu_temp/state", str(temp))
                
            time.sleep(300)
    except KeyboardInterrupt:
        pass
    finally:
        diag_client.loop_stop()
        diag_client.disconnect()

def main():
    cfg = config.load_config()
    
    broker = cfg["mqtt"]["broker"]
    port = cfg["mqtt"].get("port", 1883)
    user = cfg["mqtt"].get("username")
    pwd = cfg["mqtt"].get("password")
    client_id = cfg["mqtt"].get("client_id", "kiosk-pi")
    topic_prefix = cfg["mqtt"].get("topic_prefix", "kiosk/pi")
    
    client = mqtt.Client(client_id=client_id)
    if user and pwd:
        client.username_pw_set(user, pwd)

    def on_connect(c, userdata, flags, rc):
        print(f"Connected to MQTT broker with result code {rc}")
        
        for t in ["url/set", "screen/set", "orientation/set", "refresh/set", "reboot/set"]:
            c.subscribe(f"{topic_prefix}/{t}")
        
        discovery.publish_discovery(c, client_id, topic_prefix)
        
        current_url = cfg.get("kiosk", {}).get("default_url", "https://example.com")
        c.publish(f"{topic_prefix}/screen/state", hardware.get_screen_power(), retain=True)
        c.publish(f"{topic_prefix}/orientation/state", hardware.get_orientation(), retain=True)
        c.publish(f"{topic_prefix}/url/state", current_url, retain=True)
        
        print(f"Restoring saved URL on boot: {current_url}")
        hardware.run_cogctl("open", current_url, retries=10, delay=3.0)

    def on_message(c, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode().strip()
        print(f"Received message on {topic}: {payload}")
        
        if topic == f"{topic_prefix}/url/set":
            if hardware.run_cogctl("open", payload, retries=3, delay=2.0):
                config.update_config_url(payload)
                c.publish(f"{topic_prefix}/url/state", payload, retain=True)
            else:
                print(f"Error opening URL: {payload}", file=sys.stderr)
                
        elif topic == f"{topic_prefix}/screen/set":
            if payload in ["ON", "OFF"]:
                if hardware.set_screen_power(payload):
                    c.publish(f"{topic_prefix}/screen/state", payload, retain=True)
                    
        elif topic == f"{topic_prefix}/orientation/set":
            if payload in ["landscape", "portrait", "landscape-inverted", "portrait-inverted"]:
                if hardware.update_rotation(payload):
                    c.publish(f"{topic_prefix}/orientation/state", payload, retain=True)
                    
        elif topic == f"{topic_prefix}/refresh/set":
            hardware.restart_kiosk_service()
                
        elif topic == f"{topic_prefix}/reboot/set":
            print("Rebooting system...")
            subprocess.run(["sudo", "reboot"])

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(broker, port, 60)
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}", file=sys.stderr)
        sys.exit(1)

    diag_process = multiprocessing.Process(
        target=diagnostic_loop, 
        args=(broker, port, user, pwd, client_id, topic_prefix)
    )
    diag_process.start()

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        diag_process.terminate()
        diag_process.join()

if __name__ == "__main__":
    main()
