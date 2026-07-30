#!/usr/bin/env python3
import os
import sys
import time
import re
import json
import subprocess
import tomllib
import paho.mqtt.client as mqtt

CONFIG_PATH = "/home/kiosk/.config/kiosk-mqtt-bridge/config.toml"

# Load Configuration
def load_config():
    try:
        with open(CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        print(f"Error loading config from {CONFIG_PATH}: {e}", file=sys.stderr)
        sys.exit(1)

config = load_config()
MQTT_BROKER = config["mqtt"]["broker"]

def update_config_url(new_url):
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            if line.strip().startswith("default_url"):
                lines[i] = f'default_url = "{new_url}"\n'
                break
                
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return True
    except Exception as e:
        print(f"Error updating config.toml: {e}", file=sys.stderr)
        return False

MQTT_PORT = config["mqtt"].get("port", 1883)
MQTT_USER = config["mqtt"].get("username")
MQTT_PASSWORD = config["mqtt"].get("password")
CLIENT_ID = config["mqtt"].get("client_id", "kiosk-pi")
TOPIC_PREFIX = config["mqtt"].get("topic_prefix", "kiosk/pi")

def run_cogctl(action, arg=None, retries=5, delay=3.0):
    """Executes cogctl commands (open, reload) with retry logic to handle D-Bus startup latency."""
    cmd = ["cogctl", action]
    if arg:
        cmd.append(arg)
    
    env = dict(os.environ)
    env["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=/run/user/1001/bus"
    
    for attempt in range(1, retries + 1):
        try:
            result = subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
            print(f"cogctl {action} succeeded on attempt {attempt}")
            return True
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.strip() if e.stderr else str(e)
            print(f"cogctl {action} attempt {attempt}/{retries} failed: {err_msg}", file=sys.stderr)
            if attempt < retries:
                time.sleep(delay)
    return False

def restart_kiosk_service():
    """Single Source of Truth: Restarts kiosk.service and restores active saved URL."""
    try:
        subprocess.run(["sudo", "systemctl", "restart", "kiosk.service"], check=True)
        current_url = config.get("kiosk", {}).get("default_url", "https://example.com")
        print(f"Restoring saved URL after kiosk restart: {current_url}")
        return run_cogctl("open", current_url, retries=10, delay=2.0)
    except Exception as e:
        print(f"Error restarting kiosk.service: {e}", file=sys.stderr)
        return False

# Diagnostics Functions (Zero-Overhead /proc and /sys reads)
def get_wifi_rssi():
    try:
        with open("/proc/net/wireless", "r") as f:
            lines = f.readlines()
        for line in lines:
            if "wlan0" in line:
                parts = line.split()
                rssi = int(float(parts[3].replace(".", "")))
                return rssi
    except Exception:
        pass
    return None

def get_free_mem():
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if "MemAvailable" in line:
                    return int(line.split()[1]) // 1024  # Convert KB to MB
    except Exception:
        pass
    return None

def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return round(int(f.read().strip()) / 1000.0, 1)
    except Exception:
        pass
    return None

# Screen Power Functions
def get_screen_power():
    try:
        with open("/sys/class/graphics/fb0/blank", "r") as f:
            val = f.read().strip()
        return "OFF" if val == "1" else "ON"
    except Exception:
        return "ON"

def set_screen_power(state):
    try:
        if state == "OFF":
            subprocess.run(["sudo", "systemctl", "stop", "kiosk.service"], check=True)
            subprocess.run(["sudo", "tee", "/sys/class/graphics/fb0/blank"], input=b"1", check=True, stdout=subprocess.DEVNULL)
        else:
            subprocess.run(["sudo", "tee", "/sys/class/graphics/fb0/blank"], input=b"0", check=True, stdout=subprocess.DEVNULL)
            restart_kiosk_service()
        return True
    except Exception as e:
        print(f"Error setting screen power to {state}: {e}", file=sys.stderr)
        return False

# Screen Orientation Functions
def get_orientation():
    try:
        with open("/etc/default/kiosk", "r") as f:
            content = f.read()
        match = re.search(r"KIOSK_ROTATION=(\d+)", content)
        if match:
            rot = match.group(1)
            if rot == "1": return "portrait"
            if rot == "2": return "landscape-inverted"
            if rot == "3": return "portrait-inverted"
        return "landscape"
    except Exception:
        return "landscape"

def update_rotation(orientation):
    rotation_map = {
        "landscape": "0",
        "portrait": "1",
        "landscape-inverted": "2",
        "portrait-inverted": "3"
    }
    rot_val = rotation_map.get(orientation, "0")
    try:
        content = f"KIOSK_ROTATION={rot_val}\n"
        subprocess.run(["sudo", "tee", "/etc/default/kiosk"], input=content.encode(), check=True, stdout=subprocess.DEVNULL)
        print(f"Updated /etc/default/kiosk to KIOSK_ROTATION={rot_val}. Restarting kiosk service...")
        return restart_kiosk_service()
    except Exception as e:
        print(f"Error updating rotation: {e}", file=sys.stderr)
        return False

# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")
    
    # Subscribe to command topics
    client.subscribe(f"{TOPIC_PREFIX}/url/set")
    client.subscribe(f"{TOPIC_PREFIX}/screen/set")
    client.subscribe(f"{TOPIC_PREFIX}/orientation/set")
    client.subscribe(f"{TOPIC_PREFIX}/refresh/set")
    client.subscribe(f"{TOPIC_PREFIX}/reboot/set")
    
    # Publish Home Assistant Discovery Payloads
    device_info = {
        "identifiers": [CLIENT_ID],
        "name": "Raspberry Pi Kiosk",
        "model": "Pi 1 Model A+",
        "manufacturer": "Raspberry Pi",
        "sw_version": "1.0"
    }
    
    discovery_configs = {
        "text": {
            "url": {
                "name": "Kiosk URL",
                "unique_id": f"{CLIENT_ID}_url",
                "state_topic": f"{TOPIC_PREFIX}/url/state",
                "command_topic": f"{TOPIC_PREFIX}/url/set",
                "device": device_info
            }
        },
        "switch": {
            "screen": {
                "name": "Screen Power",
                "unique_id": f"{CLIENT_ID}_screen",
                "state_topic": f"{TOPIC_PREFIX}/screen/state",
                "command_topic": f"{TOPIC_PREFIX}/screen/set",
                "device": device_info
            }
        },
        "select": {
            "orientation": {
                "name": "Screen Orientation",
                "unique_id": f"{CLIENT_ID}_orientation",
                "state_topic": f"{TOPIC_PREFIX}/orientation/state",
                "command_topic": f"{TOPIC_PREFIX}/orientation/set",
                "options": ["landscape", "portrait", "landscape-inverted", "portrait-inverted"],
                "device": device_info
            }
        },
        "button": {
            "refresh": {
                "name": "Kiosk Refresh",
                "unique_id": f"{CLIENT_ID}_refresh",
                "command_topic": f"{TOPIC_PREFIX}/refresh/set",
                "device": device_info
            },
            "reboot": {
                "name": "System Reboot",
                "unique_id": f"{CLIENT_ID}_reboot",
                "command_topic": f"{TOPIC_PREFIX}/reboot/set",
                "device": device_info
            }
        },
        "sensor": {
            "wifi_rssi": {
                "name": "Wi-Fi RSSI",
                "unique_id": f"{CLIENT_ID}_wifi_rssi",
                "state_topic": f"{TOPIC_PREFIX}/wifi_rssi/state",
                "unit_of_measurement": "dBm",
                "device_class": "signal_strength",
                "device": device_info
            },
            "free_mem": {
                "name": "Free Memory",
                "unique_id": f"{CLIENT_ID}_free_mem",
                "state_topic": f"{TOPIC_PREFIX}/free_mem/state",
                "unit_of_measurement": "MB",
                "device": device_info
            },
            "cpu_temp": {
                "name": "CPU Temperature",
                "unique_id": f"{CLIENT_ID}_cpu_temp",
                "state_topic": f"{TOPIC_PREFIX}/cpu_temp/state",
                "unit_of_measurement": "°C",
                "device_class": "temperature",
                "device": device_info
            }
        }
    }
    
    for component, entities in discovery_configs.items():
        for object_id, payload in entities.items():
            topic = f"homeassistant/{component}/{CLIENT_ID}/{object_id}/config"
            client.publish(topic, json.dumps(payload), retain=True)
            
    # Read current default_url from config
    current_url = config.get("kiosk", {}).get("default_url", "https://example.com")
    
    # Publish Initial States
    client.publish(f"{TOPIC_PREFIX}/screen/state", get_screen_power(), retain=True)
    client.publish(f"{TOPIC_PREFIX}/orientation/state", get_orientation(), retain=True)
    client.publish(f"{TOPIC_PREFIX}/url/state", current_url, retain=True)
    
    # Automatically open the saved URL on startup to restore state with retry logic
    print(f"Restoring saved URL on boot: {current_url}")
    if not run_cogctl("open", current_url, retries=10, delay=3.0):
        print("Failed to restore initial URL after retries.", file=sys.stderr)

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode().strip()
    print(f"Received message on {topic}: {payload}")
    
    if topic == f"{TOPIC_PREFIX}/url/set":
        if run_cogctl("open", payload, retries=3, delay=2.0):
            update_config_url(payload)
            client.publish(f"{TOPIC_PREFIX}/url/state", payload, retain=True)
        else:
            print(f"Error opening URL: {payload}", file=sys.stderr)
            
    elif topic == f"{TOPIC_PREFIX}/screen/set":
        if payload in ["ON", "OFF"]:
            if set_screen_power(payload):
                client.publish(f"{TOPIC_PREFIX}/screen/state", payload, retain=True)
                
    elif topic == f"{TOPIC_PREFIX}/orientation/set":
        if payload in ["landscape", "portrait", "landscape-inverted", "portrait-inverted"]:
            if update_rotation(payload):
                client.publish(f"{TOPIC_PREFIX}/orientation/state", payload, retain=True)
                
    elif topic == f"{TOPIC_PREFIX}/refresh/set":
        restart_kiosk_service()
            
    elif topic == f"{TOPIC_PREFIX}/reboot/set":
        print("Rebooting system...")
        subprocess.run(["sudo", "reboot"])

# Main Loop
client = mqtt.Client(client_id=CLIENT_ID)
if MQTT_USER and MQTT_PASSWORD:
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
except Exception as e:
    print(f"Failed to connect to MQTT broker: {e}", file=sys.stderr)
    sys.exit(1)

client.loop_start()

last_diag_time = 0
DIAG_INTERVAL = 300  # 5 minutes

try:
    while True:
        now = time.time()
        if now - last_diag_time >= DIAG_INTERVAL:
            # Publish Diagnostics
            rssi = get_wifi_rssi()
            if rssi is not None:
                client.publish(f"{TOPIC_PREFIX}/wifi_rssi/state", str(rssi))
                
            mem = get_free_mem()
            if mem is not None:
                client.publish(f"{TOPIC_PREFIX}/free_mem/state", str(mem))
                
            temp = get_cpu_temp()
            if temp is not None:
                client.publish(f"{TOPIC_PREFIX}/cpu_temp/state", str(temp))
                
            last_diag_time = now
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting...")
finally:
    client.loop_stop()
    client.disconnect()
