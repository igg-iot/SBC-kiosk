#### Phase 1: The Offline Bootstrap (Python Provisioner)

The Python script running on your workstation now has a radically reduced scope. Its only job is to get the board onto the network, enable SSH, and plant the seed for the first boot.

1. **Network & Access:** Write `/boot/ssh`, `/boot/userconf.txt`, `wpa_supplicant.conf`, and the NetworkManager profiles. This satisfies your hard constraint.
2. **Kernel Quirks:** Append necessary `cmdline.txt` flags (like `regdom=US` and HDMI forcing).
3. **Payload Staging:** Copy the `kiosk-mqtt-bridge` files and the LLM-generated `first-boot.sh` into a staging directory on the SD card (e.g., `/root/payload/`).
4. **The Trigger:** Drop a one-shot `first-boot.service` into `/etc/systemd/system/` and symlink it to `multi-user.target.wants/`.

#### Phase 2: Native First Boot (Bash Script)

When the Pi boots, it connects to Wi-Fi natively. Systemd executes your `first-boot.sh` script as root. Because this script runs *inside* the target OS, you get to use standard Linux tooling.

1. **System Config:** Use `localectl set-locale LANG=en_US.UTF-8` and `timedatectl set-timezone America/Los_Angeles`. (This replaces the brittle file-swapping of `/etc/locale.gen` and symlinking `/etc/localtime`).
2. **Package Management:** Run `apt-get update && apt-get install -y cog libgles2 python3-paho-mqtt`.
3. **User Management:** Run `useradd -m -s /bin/bash kiosk` and `usermod -aG video,render,input,netdev kiosk`.
4. **Bridge Deployment:** Move the staged `kiosk-mqtt-bridge` payload to `/home/kiosk/`, apply `chown -R kiosk:kiosk`, and copy `kiosk-sudoers` to `/etc/sudoers.d/kiosk`.
5. **Service Enablement:** Run `loginctl enable-linger kiosk`, then `systemctl enable kiosk.service kiosk-mqtt-bridge.service`.
6. **Cleanup & Reboot:** The script disables and deletes its own `first-boot.service` so it never runs again, and issues a `reboot`.

### Why This is Better for Your Dev-CLI

1. **LLMs are Better at Bash:** Asking an LLM to "write a bash script to create a user and install packages" yields a 99% success rate. Asking an LLM to "write Python code to manually parse and modify a Linux `/etc/group` file offline" is an invitation for regex bugs and corrupted file systems.
2. **Resilience:** If `apt-get` fails because the Wi-Fi took an extra 10 seconds to connect, a native bash script can easily implement a `while ! ping -c 1 google.com; do sleep 5; done` wait-loop. Trying to account for that offline is impossible.
3. **Cross-Platform Portability:** Your workstation Python provisioner no longer cares if the target OS uses `systemd-timesyncd` or `ntpd`. It just passes the timezone string to the bash script, and the bash script uses the native tools to apply it.

## Implementation details

### The Home Directory Staging Strategy

Instead of scattering files, the Python provisioner will do the following while the SD card is mounted on the provisioning host:

1. Create `/home/kiosk/bridge/` on the `rootfs`.
2. Copy all the Python files (`main.py`, `config.py`, `hardware.py`, etc.) directly into that folder.
3. Copy the `first-boot.sh` script into `/home/kiosk/`.
4. Copy all `.service` files to `/etc/systemd/system/`.

When the bridge runs later, its systemd service will simply use `WorkingDirectory=/home/kiosk/bridge` and `ExecStart=/usr/bin/python3 main.py`. Everything stays tightly contained.