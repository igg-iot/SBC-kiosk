# RPi1-Kiosk Project Knowledge Vault

- **Target Hardware & Power Limits**: Raspberry Pi 1 Model A+ with 512MB RAM, outputting to a 1080p HDMI monitor. The single-core CPU has severe resource constraints; avoid excessive concurrent compilation or heavy software-rendering loads that peg the CPU at 100%. Operating an Edimax Wi-Fi adapter directly from the onboard USB port under high TX load can cause boot-time brownouts unless a robust 2.5A power supply is used. If brownouts persist, a powered USB hub is required.
- **Target Hostname & Credentials**:
  * **Hostname**: `raspberrypi.local` (mDNS)
  * **Admin User**: `gemini` (member of `sudo` group)
  * **Kiosk User**: `kiosk` (unprivileged, member of `video`, `render`, `input`, `netdev` groups)
- **Target GUI Architecture**: Minimalist display stack relying on **WPE WebKit + Cog** running directly on the GPU DRM/KMS framebuffer without the overhead of X11 or Wayland. This provides hardware-accelerated rendering on the VideoCore IV GPU while keeping memory usage extremely low (under 150MB total system RAM).
- **Forced HDMI Output & Rotation**:
  * To prevent `cog` from crash-looping with `Failed to initialize DRM` when booted headless, append `video=HDMI-A-1:1024x768@60D` to `/boot/firmware/cmdline.txt`. The trailing `D` forces the HDMI output to be active.
  * To rotate the screen at the kernel/driver level, append `,rotate=90` (or `180`, `270`) to the `video` parameter (e.g., `video=HDMI-A-1:1024x768@60D,rotate=90`).
- **KMS-Native Screen Power Control (DPMS)**:
  * Under full KMS (`vc4-kms-v3d`), legacy firmware-level commands like `vcgencmd display_power` are ignored.
  * To control screen power, write directly to `/sys/class/graphics/fb0/blank` (`1` to blank/turn off, `0` to unblank/turn on).
- **Shared D-Bus Session Bus & Lingering**:
  * To allow `cogctl` to dynamically control the browser (e.g., changing URLs, reloading) from other sessions or services, `cog` must run with `Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1001/bus`.
  * To ensure this D-Bus socket is initialized and maintained on boot without an interactive login, enable systemd lingering for the `kiosk` user: `sudo loginctl enable-linger kiosk`.
- **Modular Workspace Template Files**:
  * `wifi-init.service`: Systemd service to unblock Wi-Fi and set the regulatory domain on boot.
  * `disable-random-mac.conf`: NetworkManager configuration to disable MAC randomization during scanning (prevents hangs on legacy Edimax driver).
  * `kiosk.service`: Systemd service to run the `cog` web kiosk as the unprivileged `kiosk` user.
  * `kiosk-sudoers`: Sudoers rules granting the `kiosk` user passwordless privilege to reboot, poweroff, restart the kiosk service, and control screen power.
  * `kiosk-mqtt-bridge.py`: Lightweight Python MQTT daemon with zero-overhead diagnostics and HA discovery.
  * `kiosk-mqtt-bridge.service`: Systemd service to run the MQTT bridge as the `kiosk` user.
- **NetworkManager Soft-Block & Regulatory Domain**: Raspberry Pi OS (Bookworm+) defaults to soft-blocking wireless interfaces on boot, keeping the interface `DOWN` and preventing NetworkManager from initiating scans. While appending `cfg80211.ieee80211_regdom=US` to `/boot/cmdline.txt` successfully sets the global regulatory domain, the physical device (`phy#0`) initialized by the `rtl8192cu` driver still defaults to its internal EEPROM state (`DFS-UNSET`/country 99) and remains soft-blocked. To fully unblock and synchronize the physical device, a systemd boot service (`wifi-init.service`) must execute `rfkill unblock wifi` and `iw reg set US` on boot.
- **NetworkManager Connection Profiles**: Connection profiles must be stored in `/etc/NetworkManager/system-connections/` with strict `0600` permissions and owned by `root:root` to be recognized by NetworkManager on boot.
- **Edimax MAC Randomization Conflict**: The legacy `rtl8192cu` driver does not support MAC address randomization during scanning. Leaving randomization enabled causes NetworkManager scans to hang or return empty results. To ensure stable scanning and DHCP leases, create `/etc/NetworkManager/conf.d/disable-random-mac.conf` with:
  ```ini
  [device]
  wifi.scan-rand-mac-address=no
  ```
- **Modern Driver Limits**: Modern Raspberry Pi OS (Bookworm, kernel 6.x) uses the in-kernel `rtl8192cu` driver for Edimax EW-7811Un. This driver does NOT support legacy power-saving parameters like `ips`, `fwlps`, `rtw_power_mgmt`, or `rtw_enusbss`. Do not create modprobe configs with these options, as they will fail to load.
- **RPi 1 A+ Headless Provisioning Runbook**:
  1. Add `enable_uart=1` to `config.txt`.
  2. Create an empty `ssh` file in `bootfs`.
  3. Create `userconf.txt` with a hashed password (e.g., `pi:$6$...`) to bypass the first-boot wizard.
  4. Create `wpa_supplicant.conf` for Wi-Fi.
  5. Note that the Pi 1 A+ can power an Edimax Wi-Fi adapter directly without a hub if using a robust 2.5A power supply; boot delays during Wi-Fi init are normal and not brownouts.

- **WebKit Low-Memory Tuning for 512MB Pi 1**:
  * `WEBKIT_DISABLE_DMABUF_RENDERER=1`: Bypasses WPE WebKit's fragile `wpe_dmabuf_pool` queue manager on VideoCore IV, preventing `SIGSEGV` (status=11) crashes during dynamic DOM/canvas updates.
  * `WPE_WEB_PROCESS_MAX_COUNT=1`: Restricts WebKit rendering to a single WebProcess, preventing memory leaks from orphaned background processes.
  * `JSGC_EXTRA_MEMORY_THRESHOLD=1`: Forces JavaScriptCore to run aggressive Garbage Collection on tiny memory increments rather than allowing JS heap growth over time.
  * `G_SLICE=always-malloc`: Disables GLib's internal memory slice caching, forcing freed RAM to be returned directly to the OS.
- **KMS Display Scaling vs Monitor Links**:
  * Passing `video=HDMI-A-1:1024x768@60D` in `cmdline.txt` causes WebKit to render into a 1024x768 framebuffer.
  * VideoCore IV Hardware Video Scaler (HVS) hardware-upscales this 1024x768 image to a native 1080p (1920x1080) HDMI wire signal, allowing monitors to report receiving 1080p while saving ~2.7x RAM rendering footprint inside WebKit.

# Kiosk System Orchestration Guide

## 1. Operational Shift

The system has moved from a `systemd`-managed browser to a `kiosk-wrapper.sh` managed lifecycle. This eliminates "crash-cycling" by delegating process management to a script that polls hardware status, ensuring the browser only runs when the monitor is active.

## 2. Orchestration Logic

- **Polling:** The wrapper polls `/sys/class/drm/card0-HDMI-A-1/status` to determine monitor connection state.
- **Bridge Synchronization:** Cog is launched as a background process. The script waits 5 seconds for GPU initialization before restarting the `kiosk-mqtt-bridge`. This forces the bridge to re-sync and issue the "Takeover URL" command only after the browser is confirmed visible, eliminating race conditions.

## 3. Execution Flow

1. **System Startup:** Wrapper starts.
2. **Monitor OFF:** Wrapper detects `disconnected` and loops with a 10s sleep (0% CPU/IO usage).
3. **Monitor ON:** Wrapper detects `connected`, launches Cog, waits 5s, restarts the bridge, then blocks (`wait $COG_PID`) until Cog exits.
4. **Cleanup:** Once Cog dies, the loop resumes polling.

## 4. Maintenance

- **Logs:** Debugging should focus on the wrapper script output.
- **Configuration:** The wrapper remains intentionally configuration-agnostic; the Bridge service remains the single source of truth for URL state.
