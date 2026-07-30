#!/usr/bin/env python3
import sys
import time
import subprocess
import paho.mqtt.client as mqtt
from multiprocessing import Process

import config
import discovery
import hardware

def diagnostic_loop(broker, port, user, password, client_id, topic_prefix):
    """Runs in a separate process to poll hardware without blocking the main event loop."""
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
    
    MQTT_BROKER = cfg["mqtt"]["broker"]
    MQTT_PORT = cfg["mqtt"].get("port", 1883)
    MQTT_USER = cfg["mqtt"].get("username")
    MQTT_PASSWORD = cfg["mqtt"].get("password")
    CLIENT_ID = cfg["mqtt"].get("client_id", "kiosk-pi")
    TOPIC_PREFIX = cfg["mqtt"].get("topic_prefix", "kiosk/pi")

    client = mqtt.Client(client_id=CLIENT_ID)
    if MQTT_USER and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

    def on_connect(c, userdata, flags, rc):
        print(f"Connected to MQTT broker with result code {rc}")
        
        # Subscribe to command topics
        c.subscribe(f"{TOPIC_PREFIX}/url/set")
        c.subscribe(f"{TOPIC_PREFIX}/screen/set")
        c.subscribe(f"{TOPIC_PREFIX}/orientation/set")
        c.subscribe(f"{TOPIC_PREFIX}/refresh/set")
        c.subscribe(f"{TOPIC_PREFIX}/reboot/set")
        
        # Publish Home Assistant Discovery Payloads
        discovery.publish_discovery(c, CLIENT_ID, TOPIC_PREFIX)
        
        # Read current default_url from config
        current_url = cfg.get("kiosk", {}).get("default_url", "https://example.com")
        
        # Publish Initial States
        c.publish(f"{TOPIC_PREFIX}/screen/state", hardware.get_screen_power(), retain=True)
        c.publish(f"{TOPIC_PREFIX}/orientation/state", hardware.get_orientation(), retain=True)
        c.publish(f"{TOPIC_PREFIX}/url/state", current_url, retain=True)
        
        # Automatically open the saved URL on startup to restore state with retry logic
        print(f"Restoring saved URL on boot: {current_url}")
        if not hardware.run_cogctl("open", current_url, retries=10, delay=3.0):
            print("Failed to restore initial URL after retries.", file=sys.stderr)

    def on_message(c, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode().strip()
        print(f"Received message on {topic}: {payload}")
        
        if topic == f"{TOPIC_PREFIX}/url/set":
            if hardware.run_cogctl("open", payload, retries=3, delay=2.0):
                config.update_config_url(payload)
                c.publish(f"{TOPIC_PREFIX}/url/state", payload, retain=True)
            else:
                print(f"Error opening URL: {payload}", file=sys.stderr)
                
        elif topic == f"{TOPIC_PREFIX}/screen/set":
            if payload in ["ON", "OFF"]:
                if hardware.set_screen_power(payload):
                    c.publish(f"{TOPIC_PREFIX}/screen/state", payload, retain=True)
                    
        elif topic == f"{TOPIC_PREFIX}/orientation/set":
            if payload in ["landscape", "portrait", "landscape-inverted", "portrait-inverted"]:
                if hardware.update_rotation(payload):
                    c.publish(f"{TOPIC_PREFIX}/orientation/state", payload, retain=True)
                    
        elif topic == f"{TOPIC_PREFIX}/refresh/set":
            hardware.restart_kiosk_service()
            current_url = cfg.get("kiosk", {}).get("default_url", "https://example.com")
            hardware.run_cogctl("open", current_url, retries=10, delay=2.0)
                
        elif topic == f"{TOPIC_PREFIX}/reboot/set":
            print("Rebooting system...")
            subprocess.run(["sudo", "reboot"])

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}", file=sys.stderr)
        sys.exit(1)

    # Launch diagnostics in a concurrent multiprocessing process
    diag_process = Process(
        target=diagnostic_loop, 
        args=(MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD, CLIENT_ID, TOPIC_PREFIX)
    )
    diag_process.start()

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        diag_process.terminate()
        diag_process.join()
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
