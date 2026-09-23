#!/bin/bash
set -e

echo "1. Installing base cockpit (ARMv6 native from Raspbian)..."
sudo apt install -y cockpit xz-utils

echo "2. Querying native Debian Trixie-Backports index for the latest cockpit-files pointer..."
# Targeting trixie-backports because Trixie is stable, and using .xz compression.
INDEX_URL="http://deb.debian.org/debian/dists/trixie-backports/main/binary-all/Packages.xz"

# Decoupled download traps HTTP errors
wget -qO /tmp/Packages.xz "$INDEX_URL" || { echo "Fatal Error: HTTP request failed for $INDEX_URL" >&2; exit 1; }

# Decompress in memory, extract target file path, and sort
PACKAGE_PATH=$(xz -dc /tmp/Packages.xz | grep "^Filename: pool/main/c/cockpit-files/cockpit-files_" | awk '{print $2}' | sort -V | tail -n 1)

if [ -z "$PACKAGE_PATH" ]; then
    echo "Fatal Error: Could not locate cockpit-files in the extracted Debian index." >&2
    rm -f /tmp/Packages.xz
    exit 1
fi

FULL_URL="http://deb.debian.org/debian/$PACKAGE_PATH"
echo "Resolved target URL: $FULL_URL"

echo "3. Downloading the raw data payload..."
wget -O /tmp/cockpit-files.deb "$FULL_URL"

echo "4. Injecting into local package manager..."
sudo apt install -y /tmp/cockpit-files.deb

echo "5. Scrubbing temporary files..."
rm -f /tmp/cockpit-files.deb /tmp/Packages.xz

echo "Deployment complete. Web interface listening on port 9090."
