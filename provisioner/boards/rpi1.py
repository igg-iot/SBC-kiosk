import os
import uuid
from pathlib import Path
from provisioner.core.utils import generate_sha512_hash, write_file

def execute_recipe(boot_path: Path, root_path: Path, config: dict):
    print("--- Executing RPi1 Hardware Provisioning ---")

    # 1. Enable SSH
    print("Enabling SSH...")
    write_file(boot_path / "ssh", "", mode=0o644)

    # 2. Create User Account
    print("Hashing password and creating userconf.txt...")
    admin_user = config["os"]["admin_username"]
    admin_pass = config["os"]["admin_password"]
    pass_hash = generate_sha512_hash(admin_pass)
    write_file(boot_path / "userconf.txt", f"{admin_user}:{pass_hash}\n", mode=0o600)

    # 3. Set Wi-Fi Country Code (wpa_supplicant fallback & cmdline.txt regdom)
    print("Writing wpa_supplicant.conf fallback and setting regdom in cmdline.txt...")
    wpa_content = "ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\nupdate_config=1\ncountry=US\n"
    for network in config.get("wifi", []):
        wpa_content += f"""
network={{
    ssid="{network['ssid']}"
    psk="{network['psk']}"
}}
"""
    write_file(boot_path / "wpa_supplicant.conf", wpa_content, mode=0o600)

    # Find cmdline.txt location
    cmdline_path = None
    cmdline_paths = [os.path.join(boot_path, "firmware", "cmdline.txt"), os.path.join(boot_path, "cmdline.txt")]
    for path in cmdline_paths:
        if path.exists():
            cmdline_path = path
            break
    if cmdline_path is none:
        print (f"cmdline.txt was not found on SD card in {",".join(cmdline_paths)}")
        sys.exit(1)

    # Append regdom to cmdline.txt to unblock rfkill on Bookworm+ NetworkManager
    cmdline = new_cmdline = cmdline_path.read_text(encoding='utf-8').strip()
    if "cfg80211.ieee80211_regdom" not in cmdline:
        new_cmdline = f"{new_cmdline} cfg80211.ieee80211_regdom=US"
    if "video=" not in cmdline:
        new_cmdline = f"{new_cmdline} video=HDMI-A-1:{config['kiosk']['video']}"
    else:
        print (f'Unexpected "video=" setting found in cmdline.txt:\n{cmdline}')
        sys.exit(1)
    cmdline_path.write_text(new_cmdline+"\n", encoding='utf-8')
    print("Successfully appended US regdom and video settings to cmdline.txt")

    # 4. Disable MAC Randomization
    print("Disabling MAC randomization in NetworkManager...")
    mac_conf = "[device]\nwifi.scan-rand-mac-address=no\n"
    mac_path = root_path / "etc/NetworkManager/conf.d/disable-random-mac.conf"
    write_file(mac_path, mac_conf, mode=0o644)
    os.chown(mac_path, 0, 0)

    # 5. Pre-configure NetworkManager Connections
    print("Writing NetworkManager connection profiles...")
    for network in config.get("wifi", []):
        ssid = network['ssid']
        psk = network['psk']
        conn_uuid = str(uuid.uuid4())
        nm_content = f"""[connection]
id={ssid}
uuid={conn_uuid}
type=wifi
interface-name=wlan0

[wifi]
mode=infrastructure
ssid={ssid}

[wifi-security]
auth-alg=open
key-mgmt=wpa-psk
psk={psk}

[ipv4]
method=auto

[ipv6]
method=auto
addr-gen-mode=default
"""
        nm_path = root_path / "etc/NetworkManager/system-connections" / f"{ssid.replace(' ', '_')}.nmconnection"
        write_file(nm_path, nm_content, mode=0o600)
        os.chown(nm_path, 0, 0)

    # Pre-populate NetworkManager State File
    print("Pre-populating NetworkManager state file...")
    nm_state_content = "[main]\nNetworkingEnabled=true\nWirelessEnabled=true\nWWANEnabled=true\n"
    nm_state_path = root_path / "var/lib/NetworkManager/NetworkManager.state"
    write_file(nm_state_path, nm_state_content, mode=0o644)
    os.chown(nm_state_path, 0, 0)

    # 6. Create and Enable Wi-Fi Initialization Service
    print("Creating and enabling Wi-Fi initialization service...")
    service_content = """[Unit]
Description=Initialize Wi-Fi and Regulatory Domain
Before=NetworkManager.service
Before=network-online.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c "rfkill unblock wifi"
ExecStart=/bin/sh -c "iw reg set US"
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"""
    service_path = root_path / "etc/systemd/system/wifi-init.service"
    write_file(service_path, service_content, mode=0o644)
    os.chown(service_path, 0, 0)

    wants_dir = root_path / "etc/systemd/system/multi-user.target.wants"
    wants_dir.mkdir(parents=True, exist_ok=True)
    symlink_path = wants_dir / "wifi-init.service"
    if symlink_path.exists() or symlink_path.is_symlink():
        symlink_path.unlink()
    symlink_path.symlink_to("/etc/systemd/system/wifi-init.service")
