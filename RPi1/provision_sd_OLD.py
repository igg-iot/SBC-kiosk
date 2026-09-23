#!/usr/bin/env python3
# provision_sd.py - Interactive, Modular Template SD Card Provisioner
import os
import sys
import getpass
import uuid
from pathlib import Path

def generate_sha512_hash(password):
    """Generates a SHA-512 crypt hash compatible with Linux shadow/userconf.txt."""
    # We use Python's native 'crypt' module (standard on Unix/Linux)
    try:
        import crypt
        return crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))
    except ImportError:
        print("[FATAL] The 'crypt' module is required to hash passwords securely on Linux.")
        sys.exit(1)

def write_file(path, content, mode=0o600):
    """Writes a file with strict permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    with open(os.open(path, os.O_CREAT | os.O_WRONLY, mode), 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    if os.geteuid() != 0:
        print("[ERROR] This script modifies system files on the SD card and must be run with sudo.")
        sys.exit(1)

    print("=== Raspberry Pi SD Card Provisioner ===")
    
    # 1. Resolve Mount Paths
    boot_path = Path(input("Enter path to bootfs mount [default: /media/igg/bootfs]: ").strip() or "/media/igg/bootfs")
    root_path = Path(input("Enter path to rootfs mount [default: /media/igg/rootfs]: ").strip() or "/media/igg/rootfs")

    if not boot_path.exists() or not root_path.exists():
        print(f"[ERROR] Mount paths do not exist:\n  bootfs: {boot_path}\n  rootfs: {root_path}")
        sys.exit(1)

    # 2. Securely Prompt for Credentials
    print("\n--- User Account Configuration ---")
    username = input("Enter username [default: gemini]: ").strip() or "gemini"
    password = getpass.getpass(f"Enter password for '{username}': ")
    if not password:
        print("[ERROR] Password cannot be empty.")
        sys.exit(1)

    # 2b. Prompt for Timezone
    print("\n--- Timezone Configuration ---")
    timezone = input("Enter system timezone [default: America/Los_Angeles]: ").strip() or "America/Los_Angeles"

    print("\n--- Wi-Fi Configuration ---")
    wifi_networks = []
    while True:
        ssid = input(f"Enter Wi-Fi SSID #{len(wifi_networks)+1} (or press Enter to finish): ").strip()
        if not ssid:
            if not wifi_networks:
                print("[ERROR] You must configure at least one Wi-Fi network.")
                continue
            break
        psk = getpass.getpass(f"Enter Password for '{ssid}': ")
        wifi_networks.append((ssid, psk))

    # 3. Enable SSH
    print("\n[1/9] Enabling SSH...")
    write_file(boot_path / "ssh", "", mode=0o644)

    # 4. Create User Account
    print("[2/9] Hashing password and creating userconf.txt...")
    pass_hash = generate_sha512_hash(password)
    write_file(boot_path / "userconf.txt", f"{username}:{pass_hash}\n", mode=0o600)

    # 5. Set Wi-Fi Country Code (wpa_supplicant fallback & cmdline.txt regdom)
    print("[3/9] Writing wpa_supplicant.conf fallback and setting regdom in cmdline.txt...")
    wpa_content = "ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\nupdate_config=1\ncountry=US\n"
    for ssid, psk in wifi_networks:
        wpa_content += f"""
network={{
    ssid="{ssid}"
    psk="{psk}"
}}
"""
    write_file(boot_path / "wpa_supplicant.conf", wpa_content, mode=0o600)

    # Append regdom to cmdline.txt to unblock rfkill on Bookworm+ NetworkManager
    cmdline_path = boot_path / "cmdline.txt"
    if cmdline_path.exists():
        content = cmdline_path.read_text(encoding='utf-8').strip()
        if "cfg80211.ieee80211_regdom" not in content:
            # Append with a leading space to the single line
            content = f"{content} cfg80211.ieee80211_regdom=US\n"
            cmdline_path.write_text(content, encoding='utf-8')
            print("  Successfully appended US regdom to cmdline.txt")
    else:
        print("  [WARNING] cmdline.txt not found on bootfs. Skipping regdom configuration.")

    # 6. Disable MAC Randomization
    print("[4/9] Disabling MAC randomization in NetworkManager...")
    mac_conf = """[device]
wifi.scan-rand-mac-address=no
"""
    write_file(root_path / "etc/NetworkManager/conf.d/disable-random-mac.conf", mac_conf, mode=0o644)
    os.chown(root_path / "etc/NetworkManager/conf.d/disable-random-mac.conf", 0, 0)

    # 7. Pre-configure NetworkManager Connections
    print("[5/9] Writing NetworkManager connection profiles...")
    for ssid, psk in wifi_networks:
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
        nm_path = root_path / "etc" / "NetworkManager" / "system-connections" / f"{ssid.replace(' ', '_')}.nmconnection"
        write_file(nm_path, nm_content, mode=0o600)
        os.chown(nm_path, 0, 0)

    # 7b. Pre-populate NetworkManager State File to ensure Wi-Fi is enabled
    print("  Pre-populating NetworkManager state file...")
    nm_state_content = "[main]\nNetworkingEnabled=true\nWirelessEnabled=true\nWWANEnabled=true\n"
    nm_state_path = root_path / "var" / "lib" / "NetworkManager" / "NetworkManager.state"
    write_file(nm_state_path, nm_state_content, mode=0o644)
    os.chown(nm_state_path, 0, 0)

    # 8. Set US Keyboard Layout
    print("[6/9] Setting US keyboard layout...")
    kbd_path = root_path / "etc" / "default" / "keyboard"
    if kbd_path.exists():
        content = kbd_path.read_text(encoding='utf-8')
        content = content.replace('XKBLAYOUT="gb"', 'XKBLAYOUT="us"')
        kbd_path.write_text(content, encoding='utf-8')
        os.chown(kbd_path, 0, 0)
    else:
        print("  [WARNING] /etc/default/keyboard not found on rootfs. Skipping.")

    # 9. Set US English Locale
    print("[7/9] Setting US English locale...")
    locale_gen_path = root_path / "etc" / "locale.gen"
    if locale_gen_path.exists():
        content = locale_gen_path.read_text(encoding='utf-8')
        content = content.replace('# en_US.UTF-8 UTF-8', 'en_US.UTF-8 UTF-8')
        locale_gen_path.write_text(content, encoding='utf-8')
        os.chown(locale_gen_path, 0, 0)
    else:
        print("  [WARNING] /etc/locale.gen not found on rootfs. Skipping.")

    write_file(root_path / "etc" / "default" / "locale", "LANG=en_US.UTF-8\n", mode=0o644)
    os.chown(root_path / "etc" / "default" / "locale", 0, 0)

    # 10. Set Timezone
    print("[8/9] Setting system timezone...")
    tz_path = root_path / "etc" / "timezone"
    write_file(tz_path, f"{timezone}\n", mode=0o644)
    os.chown(tz_path, 0, 0)

    # Create the /etc/localtime symlink pointing to the zoneinfo file
    localtime_path = root_path / "etc" / "localtime"
    if localtime_path.exists() or localtime_path.is_symlink():
        localtime_path.unlink()
    localtime_path.symlink_to(f"/usr/share/zoneinfo/{timezone}")

    # 11. Create and Enable Wi-Fi Initialization Service
    print("[9/9] Creating and enabling Wi-Fi initialization service...")
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
    service_path = root_path / "etc" / "systemd" / "system" / "wifi-init.service"
    write_file(service_path, service_content, mode=0o644)
    os.chown(service_path, 0, 0)

    # Enable the service by creating the multi-user.target.wants symlink
    wants_dir = root_path / "etc" / "systemd" / "system" / "multi-user.target.wants"
    wants_dir.mkdir(parents=True, exist_ok=True)
    symlink_path = wants_dir / "wifi-init.service"
    if symlink_path.exists() or symlink_path.is_symlink():
        symlink_path.unlink()
    symlink_path.symlink_to("/etc/systemd/system/wifi-init.service")

    print("\nSUCCESS: SD card provisioned successfully!")
    print("You can now unmount the SD card and boot your Raspberry Pi.")

if __name__ == "__main__":
    main()
