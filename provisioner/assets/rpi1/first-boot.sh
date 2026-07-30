#!/bin/bash
# Stop on any error
set -e

echo "Starting Kiosk First-Boot Provisioning..."

# 1. Update and Install Dependencies
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y cog libgles2 python3-paho-mqtt

# 2. Create User and Group Permissions
if ! id -u kiosk > /dev/null 2>&1; then
    useradd -m -s /bin/bash kiosk
fi
usermod -aG video,render,input,netdev kiosk

# 3. Apply Localizations
localectl set-locale LANG=en_US.UTF-8
timedatectl set-timezone America/Los_Angeles

# 4. Disable Login Prompt (Allows HDMI DPMS screen blanking)
systemctl mask getty@tty1.service

# 5. Fix Permissions on Staged Assets
chown -R kiosk:kiosk /home/kiosk/bridge
mv /home/kiosk/bridge/kiosk-sudoers /etc/sudoers.d/kiosk
chmod 0440 /etc/sudoers.d/kiosk

# 6. Enable Final Services
loginctl enable-linger kiosk
systemctl enable kiosk.service
systemctl enable kiosk-mqtt-bridge.service

# 7. Self-Destruct and Reboot
echo "Provisioning complete. Self-destructing and rebooting..."
systemctl disable kiosk-first-boot.service
rm /etc/systemd/system/kiosk-first-boot.service
rm /home/kiosk/first-boot.sh

reboot
