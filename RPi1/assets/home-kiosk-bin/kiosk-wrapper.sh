#!/bin/bash
# Path to monitor status
HDMI_STATUS="/sys/class/drm/card0-HDMI-A-1/status"
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"

CONFIG_PATH="/home/kiosk/.config/kiosk-mqtt-bridge/config.toml"

# Dynamically extract rotation, default to 0 if missing
KIOSK_ROTATION=$(python3 -c "import tomllib; print(tomllib.load(open('$CONFIG_PATH', 'rb')).get('kiosk', {}).get('orientation', 0))" 2>/dev/null || echo "0")

# Infinite loop to keep the service "Active" even when the browser is sleeping
while true; do
    # Check if monitor is connected
    if [ -f "$HDMI_STATUS" ] && [ "$(cat $HDMI_STATUS)" = "connected" ]; then
        echo "Monitor connected. Launching Cog..."
        
        # Launch Cog
        /usr/bin/cog -P drm -O renderer=gles,rotation=${KIOSK_ROTATION} \
            --webprocess-failure=restart https://example.com &
        
        # Capture Cog's PID
        COG_PID=$!
        
        # Give Cog a moment to spin up, then trigger the bridge takeover
        sleep 5
        echo "Restarting MQTT bridge to trigger URL takeover..."
        sudo systemctl restart kiosk-mqtt-bridge.service
        
        # Wait for Cog to exit
        wait $COG_PID
            
        echo "Cog exited. Waiting 5 seconds before re-checking..."
        sleep 5
    else
        # Monitor is off: Sleep to avoid CPU usage and log spamming
        sleep 10
    fi
done
