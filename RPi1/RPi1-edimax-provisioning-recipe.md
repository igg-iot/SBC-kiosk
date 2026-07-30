# Headless Provisioning Recipe: RPi 1 A+ (Debian Bookworm, Edimax Wi-Fi)

**Target Mounts:** `bootfs` (`/media/igg/bootfs`), `rootfs` (`/media/igg/rootfs`)

---

### 1. SSH & User Accounts
* **SSH:** `touch bootfs/ssh` (0644)
* **Admin User (`gemini`):** `bootfs/userconf.txt` (0600) -> `gemini:<sha512_crypt_hash>`
  * *Hash Gen:* `python3 -c 'import crypt; print(crypt.crypt("pass", crypt.mksalt(crypt.METHOD_SHA512)))'`
* **Kiosk User (`kiosk`):** Create the unprivileged `kiosk` user and add them to the necessary groups for GPU, input, and network access:
  ```bash
  sudo useradd -m -s /bin/bash kiosk
  sudo usermod -aG video,render,input,netdev kiosk
  ```

### 2. Regulatory Domain, RFKill Prevention & HDMI Output
* **Kernel Parameters:** Append ` cfg80211.ieee80211_regdom=US video=HDMI-A-1:1024x768@60` to the single line in `bootfs/cmdline.txt`.
* **Fallback Config:** `bootfs/wpa_supplicant.conf` (0600):
  ```text
  ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
  update_config=1
  country=US
  ```

### 3. NetworkManager Configuration
* **Disable MAC Randomization:** Copy local template `disable-random-mac.conf` to `rootfs/etc/NetworkManager/conf.d/disable-random-mac.conf` (0644, root:root).
* **Pre-populate NM State (Force Radio On):** `rootfs/var/lib/NetworkManager/NetworkManager.state` (0644, root:root):
  ```ini
  [main]
  NetworkingEnabled=true
  WirelessEnabled=true
  WWANEnabled=true
  ```
* **Connection Profile:** `rootfs/etc/NetworkManager/system-connections/<SSID>.nmconnection` (0600, root:root):
  ```ini
  [connection]
  id=<SSID>
  uuid=<UUID>
  type=wifi
  interface-name=wlan0

  [wifi]
  mode=infrastructure
  ssid=<SSID>

  [wifi-security]
  auth-alg=open
  key-mgmt=wpa-psk
  psk=<PSK>

  [ipv4]
  method=auto

  [ipv6]
  method=auto
  addr-gen-mode=default
  ```

### 4. Wi-Fi Initialization Service (Race Condition Fix)
* **Service Unit:** Copy local template `wifi-init.service` to `rootfs/etc/systemd/system/wifi-init.service` (0644, root:root).
* **Enable Service:** Create symlink:
  `rootfs/etc/systemd/system/multi-user.target.wants/wifi-init.service` -> `/etc/systemd/system/wifi-init.service`

### 5. Localization & Timezone
* **Keyboard:** `rootfs/etc/default/keyboard` -> Replace `XKBLAYOUT="gb"` with `XKBLAYOUT="us"`
* **Locale Gen:** `rootfs/etc/locale.gen` -> Uncomment `en_US.UTF-8 UTF-8`
* **Default Locale:** `rootfs/etc/default/locale` (0644) -> `LANG=en_US.UTF-8`
* **Timezone:** `rootfs/etc/timezone` (0644) -> `America/Los_Angeles`
* **Localtime Symlink:** `rootfs/etc/localtime` -> `/usr/share/zoneinfo/America/Los_Angeles`

---

### 6. Minimalist Web Kiosk Installation (WPE WebKit + Cog)
To run a modern, hardware-accelerated web kiosk directly on the GPU framebuffer without the overhead of X11 or Wayland:

1. **Install Cog and OpenGL ES Libraries:**
   ```bash
   sudo apt-get update && sudo apt-get install -y cog libgles2
   ```

2. **Create the Kiosk Systemd Service:** Copy local template `kiosk.service` to `rootfs/etc/systemd/system/kiosk.service` (0644, root:root).
   * *Note on `DBUS_SESSION_BUS_ADDRESS`:* Setting this to the `kiosk` user's systemd-managed D-Bus socket (UID 1001) allows `cog` to register its GApplication interface on a shared bus. This enables dynamic control of the browser (e.g., changing URLs via `cogctl open <URL>`) from other sessions or services running as the same user.

3. **Enable Systemd Lingering for Kiosk User:** This forces systemd to initialize and maintain the user's D-Bus session bus on boot:
   ```bash
   sudo loginctl enable-linger kiosk
   ```

4. **Enable the Kiosk Service:** Create the target symlink manually:
   `rootfs/etc/systemd/system/multi-user.target.wants/kiosk.service` -> `/etc/systemd/system/kiosk.service`

---

### 7. KMS-Native Screen Power Control (DPMS)
Under the full KMS driver (`vc4-kms-v3d`), legacy firmware-level commands like `vcgencmd display_power` are ignored or fail to change the state because the Linux kernel has complete control of the display pipeline.

To control screen power (DPMS) headlessly under KMS, write directly to the kernel's framebuffer blanking interface:
* **Blank Screen (Turn Off HDMI Sync):**
  ```bash
  echo 1 | sudo tee /sys/class/graphics/fb0/blank
  ```
* **Unblank Screen (Turn On HDMI Sync):**
  ```bash
  echo 0 | sudo tee /sys/class/graphics/fb0/blank
  ```
* **Read Current State:**
  ```bash
  cat /sys/class/graphics/fb0/blank
  ```
  *(Returns `1` for blanked/off, `0` for unblanked/on)*

---

### 8. Sudoers Configuration for Kiosk User
To allow the unprivileged `kiosk` user to perform system actions (reboot, poweroff, restart the kiosk service, and control screen power) without a password prompt, copy local template `kiosk-sudoers` to `/etc/sudoers.d/kiosk` (0440, root:root).

---

### 9. Kiosk MQTT Bridge Installation
To enable Home Assistant discovery and remote control of the kiosk:

1. **Install Dependencies:**
   ```bash
   sudo apt-get install -y python3-paho-mqtt
   ```

2. **Install the Bridge Script:** Copy local script `kiosk-mqtt-bridge.py` to `/usr/local/bin/kiosk-mqtt-bridge.py` (0755, root:root).

3. **Configure the Bridge:** Create `/home/kiosk/.config/kiosk-mqtt-bridge/config.toml` (0600, kiosk:kiosk) with the following structure:
   ```toml
   [mqtt]
   broker = "<BROKER_IP>"
   port = 1883
   username = "<USERNAME>"
   password = "<PASSWORD>"
   client_id = "kiosk-pi"
   topic_prefix = "kiosk/pi"

   [kiosk]
   default_url = "https://google.com"
   ```

4. **Create the Bridge Service:** Copy local template `kiosk-mqtt-bridge.service` to `/etc/systemd/system/kiosk-mqtt-bridge.service` (0644, root:root).

5. **Enable and Start the Service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now kiosk-mqtt-bridge.service
   ```
