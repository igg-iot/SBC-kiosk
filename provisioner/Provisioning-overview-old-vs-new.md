### Phase 1: Mounts & Security Initialization

- **Execution:** Script runs as root, requires paths to the mounted `bootfs` and `rootfs` partitions.  
- **SSH:** Create an empty `ssh` file in `bootfs` to enable daemon on boot.  
- **Admin User:** Generate a SHA-512 crypt hash for the admin user (e.g., `gemini`) and write it to `bootfs/userconf.txt`.  
- ⚠️ **GAP - Kiosk User:** The recipe dictates creating the `kiosk` user and adding them to the `video, render, input, netdev` groups. The current Python script does not do this. *(Note: Creating users and groups on an offline `rootfs` requires editing `/etc/passwd`, `/etc/shadow`, and `/etc/group` directly, or running a `chroot`.)*  
- ⚠️ **GAP - Sudoers:** The recipe requires copying `kiosk-sudoers` to `/etc/sudoers.d/kiosk` so the unprivileged user can restart services and control the screen. The Python script misses this step.  

### Phase 2: Hardware & Kernel Configuration

- **Wi-Fi Fallback:** Write the `wpa_supplicant.conf` file to `bootfs`.  
- **Kernel Params (`cmdline.txt`):** Append `cfg80211.ieee80211_regdom=US` to fix the Bookworm rfkill block.  
- ⚠️ **GAP - HDMI Forcing:** The recipe dictates appending `video=HDMI-A-1:1024x768@60D` (and potentially a rotation flag) to `cmdline.txt` to prevent the DRM driver from crashing if booted without a monitor. The Python script does not append this.  Note that the correct commandline is 

### Phase 3: Networking & Localization

- **NetworkManager:**
  - Disable MAC randomization.  
  - Pre-populate `NetworkManager.state` to ensure radios default to ON.  
  - Write the `.nmconnection` UUID profiles for the provided SSIDs.  
- **Race Condition Fix:** Copy `wifi-init.service` to `rootfs` and create the `multi-user.target.wants` symlink to enable it.  
- **Localization:** Modify `/etc/default/keyboard` (to US), `/etc/locale.gen`, and `/etc/default/locale` (to en_US.UTF-8).  
- **Timezone:** Write `/etc/timezone` and create the symlink for `/etc/localtime`.  

### Phase 4: Kiosk Browser Deployment

- **Service Installation:** Copy `kiosk.service` to the systemd directory.  
- **Service Enablement:** Create the `multi-user.target.wants` symlink.  
- ⚠️ **GAP - Lingering & Dependencies:** The recipe calls for running `apt-get install` (for `cog` and `libgles2`) and `loginctl enable-linger kiosk`.  
  - *Architectural Note:* You cannot natively run `apt` or `loginctl` on a mounted SD card via a Python script without QEMU emulation. If the target base image does not already have these installed/enabled, the provisioner will need to inject a "first-boot" shell script to execute these live.

### Phase 5: Kiosk MQTT Bridge Deployment (The New Additions)

- **Payload Transfer:** Create the `/home/kiosk/kiosk-mqtt-bridge/` directory on the `rootfs`. Copy the new modular codebase (`main.py`, `config.py`, `discovery.py`) into this folder.
- **Hardware Profile Translation:** Copy the specific board profile (e.g., `provisioner/boards/rpi1.py`) into the payload folder and rename it strictly to `hardware.py`.
- **Configuration Generation:** Parse the user's `provision.toml` to extract the MQTT broker, port, user, and password, and write this into `/home/kiosk/.config/kiosk-mqtt-bridge/config.toml`.  
- **Permissions:** `chown` the entire app directory and config file to the `kiosk` user's UID/GID (usually 1001).  
- **Systemd Service:** Copy `kiosk-mqtt-bridge.service` to `/etc/systemd/system/` and create the symlink in `multi-user.target.wants` to enable it on boot.  