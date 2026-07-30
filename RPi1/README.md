# Raspberry Pi 1 Headless Kiosk Provisioner

A minimalist, zero-dependency provisioning suite designed to perform pre-boot, headless configuration of a Raspberry Pi 1 SD card running Debian Bookworm+ with NetworkManager and an Edimax Wi-Fi adapter.

## System Architecture

*   **`RPi1-edimax-provisioning-recipe.md`**: The master pre-boot headless recipe detailing the manual steps required to configure SSH, user accounts, regulatory domains, NetworkManager connections, locales, keyboard layouts, and timezones.
*   **`provision_sd.py`**: The interactive, zero-dependency Python implementation of the recipe. It securely prompts for credentials, timezones, and Wi-Fi networks, hashes passwords using SHA-512 crypt, and writes the configuration files directly to the mounted SD card partitions.
*   **`assets/`**: Modular configuration templates, systemd services, and executable scripts deployed to target system locations during provisioning or maintenance.

## Deployment Asset Mapping

| Local Asset | Target RPi Path | Owner / Mode | Description |
| :--- | :--- | :--- | :--- |
| `assets/kiosk.service` | `/etc/systemd/system/kiosk.service` | `root:root` (`0644`) | Systemd service running WPE WebKit/Cog browser |
| `assets/kiosk-default` | `/etc/default/kiosk` | `root:root` (`0644`) | Kiosk environment configuration (`KIOSK_ROTATION`, `KIOSK_URL`, WebKit flags) |
| `assets/kiosk-sudoers` | `/etc/sudoers.d/kiosk` | `root:root` (`0440`) | Sudo privileges granting `kiosk` user hardware control & restart access |
| `assets/kiosk-mqtt-bridge.service` | `/etc/systemd/system/kiosk-mqtt-bridge.service` | `root:root` (`0644`) | Systemd unit running Home Assistant MQTT integration daemon |
| `assets/kiosk-mqtt-bridge.py` | `/home/kiosk/kiosk-mqtt-bridge.py` | `kiosk:kiosk` (`0755`) | Lightweight MQTT bridge daemon for HA discovery and diagnostics |
| `assets/wifi-init.service` | `/etc/systemd/system/wifi-init.service` | `root:root` (`0644`) | Systemd boot service for RF unblocking and regulatory domain sync |
| `assets/disable-random-mac.conf` | `/etc/NetworkManager/conf.d/disable-random-mac.conf` | `root:root` (`0644`) | Disables MAC randomization during scanning to prevent driver hangs |

## Execution Instructions

The provisioner modifies system files on the mounted SD card partitions and must be run with root privileges (`sudo`):

```bash
sudo python3 provision_sd.py
```

### Mount Point Requirements
Before running the script, ensure your SD card's `bootfs` and `rootfs` partitions are mounted. Typical mount points on Linux:
*   `bootfs`: `/media/$USER/bootfs`
*   `rootfs`: `/media/$USER/rootfs`
