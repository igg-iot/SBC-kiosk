import os
import subprocess
import time
import re
import sys

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

def get_screen_power():
    try:
        with open("/sys/class/graphics/fb0/blank", "r") as f:
            val = f.read().strip()
        return "OFF" if val == "1" else "ON"
    except Exception:
        return "ON"

def restart_kiosk_service():
    """Single Source of Truth: Restarts kiosk.service."""
    try:
        subprocess.run(["sudo", "systemctl", "restart", "kiosk.service"], check=True)
        return True
    except Exception as e:
        print(f"Error restarting kiosk.service: {e}", file=sys.stderr)
        return False

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
