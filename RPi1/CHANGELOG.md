# Changelog

## [Unreleased] - 2026-07-26

### Added
- **GLES Display Orientation Matrix Control**: Configured Cog's OpenGL ES renderer (`-O renderer=gles,rotation=${KIOSK_ROTATION}`) to perform GPU matrix rotation (`0`=Landscape, `1`=Portrait, `2`=Landscape-Inverted, `3`=Portrait-Inverted) in hardware shaders without requiring system reboots.
- **Systemd Environment File (`/etc/default/kiosk`)**: Created `/etc/default/kiosk` to persist runtime orientation state across boots and service restarts.
- **Hardware HDMI Display Power Control**: Integrated KMS display blanking (`/sys/class/graphics/fb0/blank`) and service lifecycle management in `set_screen_power()`, turning off physical monitor signal while saving 100% CPU/RAM when off.
- **Console Unbind (`fbcon`)**: Added `ExecStartPre` to `kiosk.service` to unbind Linux Framebuffer Console (`fbcon`), preventing text login prompts from locking display power states.

### Refactored
- **DRY Single Source of Truth (`restart_kiosk_service`)**: Unified all kiosk service restarts into `restart_kiosk_service()` in `kiosk-mqtt-bridge.py`, guaranteeing URL restoration on power-on, rotation change, and refresh events.

### Fixed
- **Boot-time D-Bus Race Condition**: Added systemd dependencies (`After=kiosk.service`, `Wants=kiosk.service`) and `run_cogctl` retry loops to ensure `cog`'s D-Bus interface (`com.igalia.Cog`) is listening before sending commands.
- **HDMI Force Digital Lock**: Removed trailing `D` flag from `video=HDMI-A-1:1024x768@60` in `/boot/firmware/cmdline.txt`, allowing kernel DRM DPMS and framebuffer blanking signals to reach physical monitor hardware.
- **Passwordless Sudo Privileges**: Updated `/etc/sudoers.d/kiosk` with rules for `/etc/default/kiosk`, `/sys/class/vtconsole/vtcon1/bind`, and service restart commands.

## [2026-07-23]

### Added
- Applied low-memory WebKit tuning parameters to `kiosk.service`:
  - `Environment=WEBKIT_DISABLE_DMABUF_RENDERER=1` (disables fragile DMA-BUF queue manager, fixing `wpe_dmabuf_pool` SIGSEGV crash).
  - `Environment=WPE_WEB_PROCESS_MAX_COUNT=1` (restricts WebKit to a single renderer process).
  - `Environment=JSGC_EXTRA_MEMORY_THRESHOLD=1` (forces aggressive JavaScript garbage collection on small heaps).
  - `Environment=G_SLICE=always-malloc` (disables GLib memory caching to return freed RAM immediately to OS).

### Changed
- Synchronized all live RPi configuration files back to local workspace templates:
  - `kiosk.service`
  - `kiosk-sudoers`
  - `wifi-init.service`
  - `disable-random-mac.conf`
  - `kiosk-mqtt-bridge.service`
  - `kiosk-mqtt-bridge.py`

### Fixed
- Identified root cause of `wpe_dmabuf_pool` queue double-free crash during dynamic page updates.
- Reduced WebKit RAM consumption by ~35 MB, increasing available system memory headroom to 150 MB.
- Clarified VideoCore IV display scaling behavior: `video=HDMI-A-1:1024x768@60D` renders a 1024x768 viewport which is hardware-scaled by VideoCore HVS to 1080p native HDMI output.

All notable changes to the Raspberry Pi 1 Kiosk project will be documented in this file in reverse-chronological order.

## [2024-07-17] - Initial Release: Headless Provisioning Suite
- **Added**: `RPi1-edimax-provisioning-recipe.md` detailing the complete pre-boot headless recipe for Bookworm+ and NetworkManager.
- **Added**: `provision_sd.py` interactive Python script implementing the recipe with secure credential prompting, SHA-512 crypt hashing, and NetworkManager profile generation.
