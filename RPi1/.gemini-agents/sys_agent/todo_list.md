# RPi1-Kiosk Project To-Do List

## Phase 2: Live Stability
- [ ] Observe long-term DAKboard rendering stability under low-memory WebKit tuning and GLES rotation

## Phase 3: Multi-Kiosk Provisioning Enhancements
- [ ] Refactor `provision_sd.py` to prompt for and bake in:
  - [ ] Unique Hostname (used for system, DHCP, mDNS, and MQTT/HA)
  - [ ] Display Orientation (Landscape, Portrait, Landscape-Inverted, Portrait-Inverted)
  - [ ] Admin (`gemini`) and Kiosk (`kiosk`) credentials
- [ ] Update `provision_sd.py` to copy modular template files directly to mounted SD card partitions:
  - [ ] `wifi-init.service`
  - [ ] `disable-random-mac.conf`
  - [ ] `kiosk.service`
  - [ ] `kiosk-default` (`/etc/default/kiosk`)
  - [ ] `kiosk-sudoers`
  - [ ] `kiosk-mqtt-bridge.service`
  - [ ] `kiosk-mqtt-bridge.py`