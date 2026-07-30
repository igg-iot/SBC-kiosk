# SBC Kiosk & MQTT Bridge

A highly modular, two-stage provisioning suite and Home Assistant MQTT bridge designed to turn Debian-based Single Board Computers (SBCs) into remotely managed, hardware-accelerated web kiosks.

This project was built to solve the classic headless deployment problem: configuring Wi-Fi, injecting secure credentials, and setting up complex browser environments on an SD card *without* needing a keyboard or monitor connected to the Pi.

## System Architecture

To ensure reliable, cross-platform deployment, this project splits the provisioning process into two distinct phases:

1. **The Offline Provisioner (`/provisioner`):** A zero-dependency Python engine that runs on your workstation (Mac, Windows, or Linux). It reads a simple `provision.toml` file, securely writes Wi-Fi configurations and passwords to the mounted SD card, and stages the deployment payload.
2. **The Native First-Boot (`first-boot.sh`):** A self-destructing systemd service that runs natively on the SBC during its first boot. It leverages the SBC's actual network connection to safely install `apt` packages, create users, and configure display managers, avoiding the brittle nature of offline file-system manipulation.

## Repository Structure

```text
SBC-kiosk/
├── kiosk-mqtt-bridge/           # 📦 The Payload (Deployed to the SBC)
│   ├── config.py                # URL state management
│   ├── discovery.py             # Home Assistant MQTT Discovery payloads
│   ├── main.py                  # Process orchestration and MQTT loop
│   └── hardware_profiles/       # Board-specific hardware commands
│
└── provisioner/                 # 🛠️ The Tool (Runs on your workstation)
    ├── provision.toml           # 📝 User configuration (Wi-Fi, MQTT, secrets)
    ├── core/                    # Engine and utilities
    ├── assets/                  # Systemd services and sudoers templates
    └── boards/                  # OS-level parsing logic for specific SBCs
```

## Features

- **Zero-Touch Deployment:** Flash a base Debian image, run the provisioner, and boot. The kiosk will handle the rest.
- **Home Assistant Auto-Discovery:** Instantly appears in Home Assistant with native device classes and Material Design icons.
- **Hardware Diagnostics:** Reports CPU temperature, Free Memory, and Wi-Fi RSSI via a non-blocking background process.
- **Full Remote Control:** Update the displayed URL, toggle screen power (using native DPMS/framebuffer blanking), change screen orientation, or reboot the system entirely over MQTT.

## Getting Started

### 1. Prerequisites

- A workstation with Python 3.11+.
- An SD card flashed with a standard Debian/Raspberry Pi OS base image.
- The `bootfs` and `rootfs` partitions of the SD card mounted on your workstation.

### 2. Configuration

Clone this repository and copy the example configuration file:

```bash
git clone https://github.com/igg-iot/SBC-kiosk.git
cd SBC-kiosk
cp provisioner/provision.example.toml provisioner/provision.toml
```

Edit `provisioner/provision.toml` with your text editor. This file contains your Wi-Fi credentials, Home Assistant MQTT broker details, and the specific mount paths for your workstation's OS.

### 3. Provision the SD Card

Run the provisioner engine with root privileges (required to write to the `rootfs` partition and apply strict `0600` file permissions):

```bash
sudo python3 provisioner/core/engine.py
```

### 4. Boot the Device

Unmount the SD card, insert it into your SBC, and power it on.

During the first boot, the system will connect to your Wi-Fi, download the required browser packages (`cog`, `wpewebkit`), deploy the Home Assistant bridge, and automatically reboot into the fully functional kiosk.

## Home Assistant Integration Details

Because this bridge utilizes MQTT Auto-Discovery, no manual YAML configuration is required in Home Assistant.

- **Controls:** We recommend using Lovelace **Button Cards** for the Reboot and Refresh entities. The bridge provisions these with native `restart` device classes and custom icons, ensuring they look great in your dashboard natively.
- **Screen Power:** DPMS screen blanking is exposed as a standard Switch entity. Toggling it off puts the monitor to sleep; toggling it on wakes the monitor and safely reloads the browser service.
- **State Restoration:** If the SBC loses power, it will automatically query its local configuration on boot and restore the last commanded URL, orientation, and screen state.