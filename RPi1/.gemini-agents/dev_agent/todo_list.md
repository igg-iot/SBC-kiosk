# RPi1-Kiosk Project To-Do List

## Phase 1: Headless Boot & Wi-Fi Debugging (Completed)
- [x] Document master pre-boot headless recipe (`RPi1-edimax-provisioning-recipe.md`)
- [x] Implement interactive SD card provisioning script (`provision_sd.py`)
- [x] Verify background execution of corrected `serial-mux` tool to capture boot logs
- [x] Verify automatic Wi-Fi connection on boot using the Edimax adapter
- [x] Debug NetworkManager connection profiles and soft-block issues over serial console
- [x] Verify SSH access using the native `ssh-exec` tool on session restart

## Phase 2: Live Kiosk Deployment & Verification (Completed)
- [x] Create unprivileged `kiosk` user with correct group memberships
- [x] Enable systemd lingering for the `kiosk` user to support shared D-Bus session control
- [x] Configure passwordless `sudo` limits for the `kiosk` user
- [x] Verify KMS-native screen power control (`/sys/class/graphics/fb0/blank`)
- [x] Verify kernel-level screen rotation (`video=HDMI-A-1:...,rotate=X`)
- [x] Copy local template files and scripts to the live Pi
- [x] Start and verify `kiosk-mqtt-bridge.service` on the live Pi

## Phase 3: Browser Stability & Crash Diagnostics (Active)
- [ ] Diagnose and resolve the browser crash (SEGV) in the `wpe_dmabuf_pool` / page-flip pipeline:
  - [ ] Connect a physical monitor to the Pi to drive hardware scanout and VBLANK interrupts (required to trigger the crash).
  - [ ] Clean up orphaned lingering `cog` processes (`sudo killall -9 cog sudo`) to free up the DRM master lock.
  - [ ] Launch the browser sandbox using `systemd-run` with `WEBKIT_SHOW_CONSOLE_MESSAGES=1` and `GST_DEBUG=3`.
  - [ ] Export the sandbox journal, transfer it locally via `scp-exec`, and analyze the untruncated logs to pinpoint the driver/GStreamer failure.
- [ ] Implement Python-side self-healing (D-Bus monitor) in `kiosk-mqtt-bridge.py` to automatically restore the saved URL after a browser crash/restart.

## Phase 4: Home Assistant & MQTT Integration (Completed)
- [x] Implement lightweight Python MQTT daemon (`kiosk-mqtt-bridge.py`) with zero-overhead diagnostics and HA discovery
- [x] Deploy and start the MQTT bridge service on the live Pi
- [x] Verify Home Assistant MQTT Discovery for:
  - [x] **Controls**: Kiosk URL (text), Screen Power (switch), Screen Orientation (select), Kiosk Refresh (button), System Reboot (button)
  - [x] **Diagnostics**: Wi-Fi RSSI (sensor), Free Memory (sensor), CPU Temperature (sensor)

## Phase 5: Multi-Kiosk Provisioning Enhancements
- [ ] Refactor `provision_sd.py` to prompt for and bake in:
  - [ ] Unique Hostname (used for system, DHCP, mDNS, and MQTT/HA)
  - [ ] Display Orientation (Landscape, Portrait, Landscape-Inverted, Portrait-Inverted)
  - [ ] Admin (`gemini`) and Kiosk (`kiosk`) credentials
- [ ] Update `provision_sd.py` to copy the modular template files directly to the mounted SD card partitions:
  - [ ] `wifi-init.service`
  - [ ] `disable-random-mac.conf`
  - [ ] `kiosk.service`
  - [ ] `kiosk-sudoers`
  - [ ] `kiosk-mqtt-bridge.service`
  - [ ] `kiosk-mqtt-bridge.py`