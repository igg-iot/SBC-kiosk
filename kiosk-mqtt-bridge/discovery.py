import json

def publish_discovery(client, client_id, topic_prefix):
    device_info = {
        "identifiers": [client_id],
        "name": "Raspberry Pi Kiosk",
        "manufacturer": "Raspberry Pi",
        "sw_version": "1.0"
    }
    
    discovery_configs = {
        "text": {
            "url": {
                "name": "Kiosk URL",
                "unique_id": f"{client_id}_url",
                "state_topic": f"{topic_prefix}/url/state",
                "command_topic": f"{topic_prefix}/url/set",
                "device": device_info
            }
        },
        "switch": {
            "screen": {
                "name": "Screen Power",
                "unique_id": f"{client_id}_screen",
                "state_topic": f"{topic_prefix}/screen/state",
                "command_topic": f"{topic_prefix}/screen/set",
                "icon": "mdi:monitor",  # Forces a screen icon instead of a toggle switch
                "device": device_info
            }
        },
        "select": {
            "orientation": {
                "name": "Screen Orientation",
                "unique_id": f"{client_id}_orientation",
                "state_topic": f"{topic_prefix}/orientation/state",
                "command_topic": f"{topic_prefix}/orientation/set",
                "options": ["landscape", "portrait", "landscape-inverted", "portrait-inverted"],
                "device": device_info
            }
        },
        "button": {
            "refresh": {
                "name": "Refresh Browser",
                "unique_id": f"{client_id}_refresh",
                "command_topic": f"{topic_prefix}/refresh/set",
                "icon": "mdi:web-refresh",          # Adds a specific browser refresh icon
                "device": device_info
            },
            "reboot": {
                "name": "System Reboot",
                "unique_id": f"{client_id}_reboot",
                "command_topic": f"{topic_prefix}/reboot/set",
                "device_class": "restart",          # Inherits standard HA restart behaviors/icons
                "device": device_info
            }
        },
        "sensor": {
            "wifi_rssi": {
                "name": "Wi-Fi RSSI",
                "unique_id": f"{client_id}_wifi_rssi",
                "state_topic": f"{topic_prefix}/wifi_rssi/state",
                "unit_of_measurement": "dBm",
                "device_class": "signal_strength",
                "device": device_info
            },
            "free_mem": {
                "name": "Free Memory",
                "unique_id": f"{client_id}_free_mem",
                "state_topic": f"{topic_prefix}/free_mem/state",
                "unit_of_measurement": "MB",
                "icon": "mdi:memory",               # Explicit icon for memory
                "device": device_info
            },
            "cpu_temp": {
                "name": "CPU Temperature",
                "unique_id": f"{client_id}_cpu_temp",
                "state_topic": f"{topic_prefix}/cpu_temp/state",
                "unit_of_measurement": "°C",
                "device_class": "temperature",
                "device": device_info
            }
        }
    }
    
    for component, entities in discovery_configs.items():
        for object_id, payload in entities.items():
            topic = f"homeassistant/{component}/{client_id}/{object_id}/config"
            client.publish(topic, json.dumps(payload), retain=True)
