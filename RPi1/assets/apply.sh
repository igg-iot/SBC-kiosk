#!/bin/bash
set -e

echo "=========================================="
echo "1. SD Card Wear Reduction & Memory Tuning"
echo "=========================================="
# Destroy physical swap file and its management service
if systemctl is-active --quiet dphys-swapfile; then
    systemctl disable --now dphys-swapfile
fi
rm -f /var/swap
DEBIAN_FRONTEND=noninteractive apt-get purge -y dphys-swapfile

# Optimize kernel parameters for zram swap
cat << 'EOF' > /etc/sysctl.d/99-zram-tuning.conf
vm.swappiness=100
vm.watermark_boost_factor=0
vm.watermark_scale_factor=125
vm.page-cluster=0
EOF
sysctl --system

# Shift systemd-journald to volatile tmpfs
sed -i 's/.*Storage=.*/Storage=volatile/' /etc/systemd/journald.conf
systemctl restart systemd-journald

echo "=========================================="
echo "2. Install Core Kiosk Dependencies"
echo "=========================================="
apt-get update
# Full dependency resolution; disk space is cheap, RAM/uptime is absolute.
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    cog \
    libwpebackend-fdo-1.0-1 \
    libwpe-1.0-1 \
    libgles2 \
    libegl1 \
    libgbm1 \
    libgl1-mesa-dri \
    fonts-dejavu-core \
    python3-paho-mqtt \
    xz-utils \
    wget \
    curl

# Fix Netplan permissions to prevent the 1m20s NetworkManager loop
chmod 600 /lib/netplan/00-network-manager-all.yaml
chmod 600 /etc/netplan/*.yaml 2>/dev/null

# Kill cloud-init to reclaim ~45s of boot time
touch /etc/cloud/cloud-init.disabled

# Avoid entropy starvation
sudo apt install haveged
sudo systemctl enable haveged
## Note that none of the above improved the 2 minute NetworkManager start.

echo "=========================================="
echo "3. Management Interface Installation"
echo "=========================================="
# Execute the Cockpit sideload script directly from the staged assets.
# Note: The underlying install-cockpit.sh will install the 'cockpit' base package.
bash /home/igg/assets/home-kiosk-bin/install-cockpit.sh

echo "=========================================="
echo "4. Kiosk User Provisioning"
echo "=========================================="
if ! id -u kiosk > /dev/null 2>&1; then
    useradd -m -u 1001 -s /bin/bash kiosk
    # Hardware DRM access requires the 'video' and 'render' groups.
    usermod -aG video,render,input,netdev kiosk
    loginctl enable-linger kiosk
fi

echo "=========================================="
echo "5. Route Configurations & Assets"
echo "=========================================="
# Environment & Network
cp /home/igg/assets/etc-default/kiosk /etc/default/kiosk
chmod 644 /etc/default/kiosk

mkdir -p /etc/NetworkManager/conf.d
cp /home/igg/assets/etc-NetworkManager-conf.d/disable-random-mac.conf /etc/NetworkManager/conf.d/
chmod 644 /etc/NetworkManager/conf.d/disable-random-mac.conf

# Sudoers
cp /home/igg/assets/etc-sudoers.d/kiosk /etc/sudoers.d/kiosk
chmod 440 /etc/sudoers.d/kiosk
chown root:root /etc/sudoers.d/kiosk

# Binaries
mkdir -p /home/kiosk/bin
cp /home/igg/assets/home-kiosk-bin/kiosk-wrapper.sh /home/kiosk/bin/
cp /home/igg/assets/home-kiosk-bin/kiosk-mqtt-bridge.py /home/kiosk/bin/
chmod 755 /home/kiosk/bin/kiosk-wrapper.sh /home/kiosk/bin/kiosk-mqtt-bridge.py
chown root:root /home/kiosk/bin/kiosk-wrapper.sh /home/kiosk/bin/kiosk-mqtt-bridge.py

# Kiosk TOML Configuration
CONFIG_DIR="/home/kiosk/.config/kiosk-mqtt-bridge"
mkdir -p ${CONFIG_DIR}
cp /home/igg/assets/config/config.toml ${CONFIG_DIR}/config.toml
chown -R kiosk:kiosk /home/kiosk/.config
chmod 600 ${CONFIG_DIR}/config.toml

# Systemd Services
cp /home/igg/assets/etc-systemd-system/kiosk.service /etc/systemd/system/
cp /home/igg/assets/etc-systemd-system/kiosk-mqtt-bridge.service /etc/systemd/system/
cp /home/igg/assets/etc-systemd-system/wifi-init.service /etc/systemd/system/
chmod 644 /etc/systemd/system/kiosk.service /etc/systemd/system/kiosk-mqtt-bridge.service /etc/systemd/system/wifi-init.service

echo "=========================================="
echo "6. Apply & Initialize"
echo "=========================================="
systemctl daemon-reload
systemctl enable --now wifi-init.service || true
systemctl enable --now kiosk.service
systemctl enable --now kiosk-mqtt-bridge.service
echo "Iteration deployed successfully."
