#!/usr/bin/env python3
import os
import sys
import shutil
import importlib
import tomllib
from pathlib import Path

def main():
    if os.geteuid() != 0:
        print("[ERROR] This script modifies system files on the SD card and must be run with sudo.")
        sys.exit(1)

    print("=== SBC Kiosk SD Card Provisioner ===")
    
    # 1. Load Configuration
    config_path = Path(__file__).parent.parent / "provision.toml"
    if not config_path.exists():
        print(f"[ERROR] Configuration file not found at {config_path}")
        sys.exit(1)
        
    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    boot_path = Path(config["system"]["bootfs_path"])
    root_path = Path(config["system"]["rootfs_path"])

    if not boot_path.exists() or not root_path.exists():
        print(f"[ERROR] Mount paths do not exist:\n  bootfs: {boot_path}\n  rootfs: {root_path}")
        sys.exit(1)

    profile = config["kiosk"].get("hardware_profile", "rpi1")
    
    # 2. Execute Board-Specific Plugin
    try:
        # Dynamically load the module (e.g., boards.rpi1)
        plugin = importlib.import_module(f"provisioner.boards.{profile}")
        plugin.execute_recipe(boot_path, root_path, config)
    except ModuleNotFoundError:
        print(f"[ERROR] Hardware profile plugin 'boards/{profile}.py' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed executing hardware profile {profile}: {e}")
        sys.exit(1)

    # 3. Stage First-Boot Assets
    print("--- Staging First-Boot Assets & Services ---")
    assets_dir = Path(__file__).parent.parent / "assets" / profile
    kiosk_home = root_path / "home/kiosk"
    kiosk_home.mkdir(parents=True, exist_ok=True)
    
    # Drop first-boot script
    shutil.copy(assets_dir / "first-boot.sh", kiosk_home / "first-boot.sh")
    
    # Drop and enable systemd services
    systemd_dir = root_path / "etc/systemd/system"
    for svc_file in assets_dir.glob("*.service"):
        shutil.copy(svc_file, systemd_dir / svc_file.name)
        
    # Enable the one-shot first-boot service
    wants_dir = systemd_dir / "multi-user.target.wants"
    wants_dir.mkdir(parents=True, exist_ok=True)
    first_boot_sym = wants_dir / "kiosk-first-boot.service"
    if first_boot_sym.exists() or first_boot_sym.is_symlink():
        first_boot_sym.unlink()
    first_boot_sym.symlink_to("/etc/systemd/system/kiosk-first-boot.service")

    # 4. Stage the MQTT Bridge Codebase
    print("--- Staging Kiosk MQTT Bridge Payload ---")
    bridge_src = Path(__file__).parent.parent.parent / "kiosk-mqtt-bridge"
    bridge_dest = kiosk_home / "bridge"
    bridge_dest.mkdir(parents=True, exist_ok=True)
    
    # Copy core python files
    for py_file in bridge_src.glob("*.py"):
        shutil.copy(py_file, bridge_dest / py_file.name)
        
    # Translate the specific hardware profile into the generic hardware.py payload
    hw_profile_src = bridge_src / "hardware_profiles" / f"{profile}.py"
    if hw_profile_src.exists():
        shutil.copy(hw_profile_src, bridge_dest / "hardware.py")
    else:
        print(f"[WARNING] Bridge hardware profile {hw_profile_src} not found. Payload may be incomplete.")

    # Drop the sudoers template into the bridge staging folder for first-boot.sh to pick up
    shutil.copy(assets_dir / "kiosk-sudoers", bridge_dest / "kiosk-sudoers")

    # 5. Generate MQTT Bridge Configuration (config.toml)
    print("Generating Kiosk MQTT Bridge config.toml...")
    bridge_config_dir = kiosk_home / ".config/kiosk-mqtt-bridge"
    bridge_config_dir.mkdir(parents=True, exist_ok=True)
    
    bridge_config_content = f"""[mqtt]
broker = "{config['mqtt']['broker']}"
port = {config['mqtt'].get('port', 1883)}
username = "{config['mqtt'].get('username', '')}"
password = "{config['mqtt'].get('password', '')}"
client_id = "{config['mqtt'].get('client_id', 'kiosk-pi')}"
topic_prefix = "{config['mqtt'].get('topic_prefix', 'kiosk/pi')}"

[kiosk]
default_url = "{config['kiosk']['default_url']}"
"""
    with open(bridge_config_dir / "config.toml", "w", encoding="utf-8") as f:
        f.write(bridge_config_content)

    # 6. Add the default screen orientation env file
    shutil.copy(assets_dir / "etc-default-kiosk", "etc" / "default" / "kiosk")


    print("\nSUCCESS: SD card provisioned successfully!")
    print("You can now unmount the SD card and boot your kiosk.")

if __name__ == "__main__":
    main()
