# Raspberry Pi 1 Headless Kiosk Provisioner

A minimalist, zero-dependency provisioning suite designed to perform pre-boot, headless configuration of a Raspberry Pi 1 SD card running Debian Bookworm+ with NetworkManager and an Edimax Wi-Fi adapter.

## System Architecture

*   **`RPi1-edimax-provisioning-recipe.md`**: The master pre-boot headless recipe detailing the manual steps required to configure SSH, user accounts, regulatory domains, NetworkManager connections, locales, keyboard layouts, and timezones.
*   **`provision_sd.py`**: The interactive, zero-dependency Python implementation of the recipe. It securely prompts for credentials, timezones, and Wi-Fi networks, hashes passwords using SHA-512 crypt, and writes the configuration files directly to the mounted SD card partitions.

## Execution Instructions

The provisioner modifies system files on the mounted SD card partitions and must be run with root privileges (`sudo`):

```bash
sudo python3 provision_sd.py
```

### Mount Point Requirements
Before running the script, ensure your SD card's `bootfs` and `rootfs` partitions are mounted. Typical mount points on Linux:
*   `bootfs`: `/media/$USER/bootfs`
*   `rootfs`: `/media/$USER/rootfs`