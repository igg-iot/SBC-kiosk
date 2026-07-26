# Session Checkpoint: dev_agent (RPi1-kiosk)

- **Active Goal**: Diagnose and resolve the browser crash (SEGV) in the `wpe_dmabuf_pool` / page-flip pipeline at 1080p with a physical monitor connected.

- **Completed Milestones**:
  1. **Identified Resolution Independence**: Discovered that the crash is not exclusive to 1080p; it occurred at 1024x768 as well when a physical monitor was attached.
  2. **Isolated Headless Stability Cause**: Proved that headless execution (without a physical monitor scanning out) bypasses hardware VBLANK interrupts and page-flip events, making the browser run stably indefinitely and rendering headless tests invalid.
  3. **Designed Zero-Loss Sandbox**: Formulated a robust sandbox strategy using `systemd-run` to capture 100% of stdout/stderr/debug logs to the journal, bypassing SSH session dependencies.
  4. **Established Safe Log-Transfer Workflow**: Created a workflow using `scp-exec` and local `READ_FILE` blocks to copy and read full log files, completely bypassing the 2000-character terminal truncation limit.

- **Active Variables/Constraints**:
  - **Hardware Limits**: Raspberry Pi 1 Model A+ (ARMv6, 512MB RAM).
  - **Resolution Constraint**: Must run at 1080p (downscaling to 720p is rejected).
  - **Physical Monitor Requirement**: A physical monitor must be connected to drive the hardware scanout loop and reproduce the crash.
  - **No Unauthorized Reboots/Kernel Changes**: Any modification to `/boot/firmware/cmdline.txt` or system reboots must have 100% mutual agreement beforehand.

- **Pending Tasks**:
  1. **Connect Physical Monitor**: Attach a physical 1080p monitor to the Pi and boot the system.
  2. **Free DRM Master Lock**: Kill orphaned lingering `cog` processes (`sudo killall -9 cog sudo`).
  3. **Launch Sandbox**: Execute the `systemd-run` sandbox with `GST_DEBUG=3` and `WEBKIT_SHOW_CONSOLE_MESSAGES=1`.
  4. **Extract & Analyze Logs**: Export the sandbox journal, transfer it locally via `scp-exec`, and read it in full via `READ_FILE` to pinpoint the driver/GStreamer failure.

- **Critical Decisions Made**:
  - Rejected headless debugging as a valid method for this specific crash due to the absence of hardware scanout interrupts.
  - Rejected downscaling to 720p to adhere to the 1080p requirement.
  - Committed to a zero-data-loss logging workflow (`systemd-run` -> `scp-exec` -> local `READ_FILE`) to bypass terminal truncation limits.