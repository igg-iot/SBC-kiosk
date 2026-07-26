# Session Checkpoint: RPi1-Kiosk GLES Display Orientation & Hardware Power Control

## 1. Active Goals (Incomplete)
*   **Offline Provisioner Refactoring**: Refactor `provision_sd.py` to copy synchronized modular template files directly to mounted SD card partitions.
*   **Long-Term Rendering Stability**: Observe long-term DAKboard WebKit stability under low-memory tuning and GLES rotation.

## 2. Completed Milestones
*   **GLES GPU Matrix Orientation**: Configured Cog's OpenGL ES renderer (`-O renderer=gles,rotation=${KIOSK_ROTATION}`) driven by `/etc/default/kiosk` for instantaneous 90°/180°/270° orientation switching without system reboots.
*   **Hardware HDMI Display Power Control**: Verified physical HDMI power down via KMS blanking (`/sys/class/graphics/fb0/blank`) and service lifecycle management in `kiosk-mqtt-bridge.py`.
*   **Console Unbinding (`fbcon`)**: Embedded `ExecStartPre` in `kiosk.service` to unbind Linux text console driver (`vtcon1`), preventing login screens from locking display power management.
*   **DRY Service Restoration (`restart_kiosk_service`)**: Unified all service restarts into a single helper function in `kiosk-mqtt-bridge.py`, guaranteeing active URL restoration on power-on, orientation change, and refresh events.
*   **Boot-Time D-Bus Race Condition Fix**: Added systemd dependencies (`After=kiosk.service`, `Wants=kiosk.service`) and `run_cogctl` retry loops to ensure `com.igalia.Cog` is active before sending commands.
*   **100% Local Workspace Synchronization**: All remote RPi configuration files (`kiosk.service`, `kiosk-sudoers`, `kiosk-default`, `kiosk-mqtt-bridge.py`, `kiosk-mqtt-bridge.service`) are updated and synced with local repository templates.

## 3. Active Variables & Constraints
*   **Target Host**: `raspberrypi.local` (mDNS)
*   **Admin User**: `gemini`
*   **Kiosk User**: `kiosk` (UID 1001)
*   **Default Orientation File**: `/etc/default/kiosk` (`KIOSK_ROTATION=1` for portrait)
*   **Hardware Limits**: Raspberry Pi 1 Model A+ (512 MB RAM, VideoCore IV GPU).
*   **Memory Footprint**: ~272 MB system RAM used under GLES portrait mode, leaving 155 MB free headroom.

## 4. Pending Tasks
*   Refactor `provision_sd.py` for multi-kiosk SD card baking with template file embedding.
*   Observe long-term DAKboard rendering stability under low-memory WebKit tuning and GLES orientation.

## 5. Critical Decisions
*   **GLES GPU Shader Matrix Rotation**: Used `-O renderer=gles,rotation=${KIOSK_ROTATION}` in Cog instead of kernel video mode swaps to allow ~2-second orientation changes without system reboots.
*   **Systemd Environment File**: Passed runtime rotation to `kiosk.service` via `EnvironmentFile=/etc/default/kiosk`, keeping unit files immutable.
*   **Console Unbind**: Unbound `vtcon1` (`fbcon`) in `ExecStartPre` to guarantee a clean black framebuffer when `cog` is not running.
*   **Single Source of Truth Restarts**: Unified all kiosk restarts in `restart_kiosk_service()` to ensure `cogctl open <saved_url>` is executed consistently.