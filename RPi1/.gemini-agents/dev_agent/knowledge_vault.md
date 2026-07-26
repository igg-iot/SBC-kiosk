- Python's native `crypt` module is deprecated in Python 3.11 and completely removed in Python 3.13. For future-proofing, `provision_sd.py` should eventually migrate to a pure-Python SHA-512 crypt implementation or use an external library like `bcrypt` or `passlib` if dependencies are permitted.
- The `os.open` with `O_CREAT | os.O_WRONLY` pattern is used to guarantee strict file creation permissions (`0600`) before writing sensitive credentials.- ### RPi1 Kiosk Project State & Hand-off Summary

#### 1. Current System State & Configuration
- **Target Host**: `gemini@raspberrypi.local` (IP: `192.168.10.211`)
- **Hardware**: Raspberry Pi 1 Model A+ (ARMv6, 512MB RAM, 1080p physical display).
- **Memory Split**: `gpu_mem=64M` and `cma-128` configured in `/boot/firmware/config.txt`.
  - *Result*: Available system RAM increased from `159MB` to `287MB` (an 80% increase).
- **MQTT Broker**: Mosquitto Broker running on `homeassistant.local:1883`.
  - *Credentials*: Isolated `mqtt/mqtt` credentials configured in Mosquitto's local logins (no HA user account).
- **Kiosk Service (`kiosk.service`)**: Completely static and simple. Runs `cog` with fallback URL `https://example.com`.
- **MQTT Bridge (`kiosk-mqtt-bridge.service`)**: Active and connected (result code `0`).
  - *URL Persistence*: Modified `kiosk-mqtt-bridge.py` to write the active URL to `config.toml` on change and restore it on boot.

#### 2. The Active Bug: Browser Crash (SEGV)
- **Symptom**: When loading the 1080p Dakboard URL, the browser crashes with a Segmentation Fault (`SEGV`, status 11) about 4 seconds into the load.
- **Warning**: `warning: queue 0xa4d07d70 destroyed while proxies still attached: wpe_dmabuf_pool#12 still attached`.
- **Analysis**:
  - `free -m` shows plenty of CPU RAM and active swap space, ruling out CPU system RAM OOM.
  - The crash is in user space (no kernel segfaults or OOM messages in `dmesg`).
  - It is highly likely a graphics memory (CMA) exhaustion or a video decoding (GStreamer) crash.

#### 3. Next Steps (Immediate Action on Restart)
1. **Stop the background kiosk**: `sudo systemctl stop kiosk.service`
2. **Run manual foreground diagnostics** to capture console and media logs:
   ```bash
   sudo -u kiosk COG_PLATFORM_DRM_CARD=/dev/dri/card0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1001/bus WEBKIT_SHOW_CONSOLE_MESSAGES=1 GST_DEBUG=3 cog --platform=drm "https://dakboard.com/app/screenPredefined?p=6684e993e8f9d953e76c8891b04f49e1"
   ```
3. **Evaluate downscaling** to 720p (`1280x720`) in `/boot/firmware/cmdline.txt` if 1080p is too heavy for the GPU.
4. **Implement Python-side self-healing** (D-Bus monitor) in `kiosk-mqtt-bridge.py` to restore the URL after a crash.
- ### RPi1 Kiosk: Physical Monitor & Page-Flip Crash Dynamics

#### 1. Critical Discoveries & Refined Diagnosis
- **Resolution Independence**: The crash is *not* exclusive to 1080p. The kernel command line was explicitly forcing `1024x768` (`video=HDMI-A-1:1024x768@60D`), and the spontaneous crashes still occurred at this resolution when the physical monitor was attached.
- **Headless Stability**: Without a physical monitor scanning out, `cog` runs perfectly stable indefinitely (tested for >1 hour) at `1024x768`.
- **The Page-Flip/VBLANK Mechanism**: The crash (`wpe_dmabuf_pool` SEGV) is a buffer-lifecycle synchronization failure. When a physical monitor is connected, the hardware drives scanout and generates VBLANK interrupts, triggering page-flip events to release buffers. Headless execution bypasses this hardware scanout loop, avoiding the race condition entirely. Therefore, **a physical monitor is a hard requirement to reproduce and diagnose the crash.**
- **Process Lingering**: Processes spawned via `sudo -u kiosk` from a `gemini` SSH session are adopted by the `kiosk` user's lingering systemd slice and survive SSH logouts.

#### 2. Sandbox & Diagnostic Runbook for Next Session
Once the physical monitor is attached and the Pi is booted:
1. **Clean up orphaned processes**: `sudo killall -9 cog sudo` (to free up the DRM master lock on `/dev/dri/card0`).
2. **Launch the Sandbox**:
   ```bash
   sudo systemd-run --unit=cog-sandbox \
     --uid=kiosk \
     --setenv=COG_PLATFORM_DRM_CARD=/dev/dri/card0 \
     --setenv=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1001/bus \
     --setenv=WEBKIT_SHOW_CONSOLE_MESSAGES=1 \
     --setenv=GST_DEBUG=3 \
     /usr/bin/cog --platform=drm "https://dakboard.com/app/screenPredefined?p=6684e993e8f9d953e76c8891b04f49e1"
   ```
3. **Export & Pull Logs (Zero Truncation)**:
   - Export journal: `journalctl -u cog-sandbox --no-pager > /tmp/cog_sandbox.log`
   - Check size: `wc -c /tmp/cog_sandbox.log`
   - Copy locally: `scp-exec gemini@raspberrypi.local:/tmp/cog_sandbox.log ./cog_sandbox.log`
   - Read locally via `<<<< READ_FILE` to preserve full context.
