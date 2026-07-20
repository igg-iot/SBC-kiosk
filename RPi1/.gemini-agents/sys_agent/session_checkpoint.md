# Session Checkpoint: RPi1-Kiosk Provisioning & Boot Verification

## 1. Active Goals (Incomplete)
*   **Live Kiosk Deployment**: Copy the local template files and scripts to the live Pi, and start/verify the `kiosk-mqtt-bridge.service`.
*   **Offline Provisioner Refactoring**: Update `provision_sd.py` to support copying the new modular template files (`wifi-init.service`, `disable-random-mac.conf`, `kiosk.service`, `kiosk-sudoers`, `kiosk-mqtt-bridge.service`, `kiosk-mqtt-bridge.py`) directly to the mounted SD card partitions.

## 2. Completed Milestones
*   **SSH Verification**: Verified SSH access to the live Pi (`raspberrypi.local`) as the `gemini` user.
*   **WPE WebKit + Cog Stack**: Successfully deployed and verified `cog` running directly on the DRM/KMS framebuffer as the unprivileged `kiosk` user, achieving a sub-150MB RAM footprint.
*   **Dynamic URL Control**: Verified sub-second, dynamic URL updates and page reloads using `cogctl` over a shared D-Bus session bus.
*   **KMS-Native Screen Power**: Verified screen blanking/unblanking by writing directly to `/sys/class/graphics/fb0/blank`.
*   **Modular Workspace Restructuring**: Extracted all configuration files, systemd services, and the MQTT bridge script into clean, modular local files in our workspace, and streamlined `RPi1-edimax-provisioning-recipe.md`.

## 3. Active Variables & Constraints
*   **Target Host**: `raspberrypi.local`
*   **Admin User**: `gemini`
*   **Kiosk User**: `kiosk` (UID 1001)
*   **Hardware Limits**: Raspberry Pi 1 Model A+ (512MB RAM, single-core ARMv6 CPU, VideoCore IV GPU).
*   **Power Constraints**: Edimax Wi-Fi adapter can cause boot-time brownouts under high TX load if the power supply is under 2.5A.
*   **Driver Constraints**: The legacy `rtl8192cu` driver in kernel 6.x does not support modern power-saving parameters or MAC address randomization during scanning.

## 4. Pending Tasks
*   Copy local template files and scripts to the live Pi.
*   Start and verify `kiosk-mqtt-bridge.service` on the live Pi.
*   Refactor `provision_sd.py` to copy the modular template files directly to the mounted SD card partitions.

## 5. Critical Decisions
*   **WPE WebKit + Cog**: Selected over Wayland/Cage/Chromium for its sub-150MB RAM footprint and native DRM/KMS acceleration.
*   **KMS-Native Screen Power**: Decided to use `/sys/class/graphics/fb0/blank` instead of `vcgencmd` because the kernel KMS driver bypasses the VideoCore firmware.
*   **Kernel-Level Rotation**: Decided to use `video=HDMI-A-1:...,rotate=X` in `cmdline.txt` for hardware-accelerated rotation, as the RPi 1 GPU does not support hardware plane rotation in `cog`.
*   **D-Bus Lingering**: Enabled systemd lingering for the `kiosk` user to ensure their D-Bus session bus is initialized and maintained on boot without an interactive login.