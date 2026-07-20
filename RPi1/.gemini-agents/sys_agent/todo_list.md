# RPi1-Kiosk Project To-Do List

## Phase 1: Headless Boot & Wi-Fi Debugging (Completed)
- [x] Document master pre-boot headless recipe (`RPi1-edimax-provisioning-recipe.md`)
- [x] Implement interactive SD card provisioning script (`provision_sd.py`)
- [x] Verify background execution of corrected `serial-mux` tool to capture boot logs
- [x] Verify automatic Wi-Fi connection on boot using the Edimax adapter
- [x] Debug NetworkManager connection profiles and soft-block issues over serial console
- [x] Verify SSH access using the native `ssh-exec` tool on session restart

## Phase 2: Live Kiosk Deployment & Verification (Active)
- [x] Create unprivileged `kiosk` user with correct group memberships
- [x] Enable systemd lingering for the `kiosk` user to support shared D-Bus session control
- [x] Configure passwordless `sudo` limits for the `kiosk` user
- [x] Verify KMS-native screen power control (`/sys/class/graphics/fb0/blank`)
- [x] Verify kernel-level screen rotation (`video=HDMI-A-1:...,rotate=X`)
- [ ] Copy local template files and scripts to the live Pi
- [ ] Start and verify `kiosk-mqtt-bridge.service` on the live Pi

## Phase 3: Multi-Kiosk Provisioning Enhancements
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

## Phase 4: Home Assistant & MQTT Integration
- [x] Implement lightweight Python MQTT daemon (`kiosk-mqtt-bridge.py`) with zero-overhead diagnostics and HA discovery
- [ ] Deploy and start the MQTT bridge service on the live Pi
- [ ] Verify Home Assistant MQTT Discovery for:
  - [ ] **Controls**: Kiosk URL (text), Screen Power (switch), Screen Orientation (select), Kiosk Refresh (button), System Reboot (button)
  - [ ] **Diagnostics**: Wi-Fi RSSI (sensor), Free Memory (sensor), CPU Temperature (sensor)