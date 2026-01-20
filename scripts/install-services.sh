#!/bin/bash
# Install Reality services for always-on operation

set -e

echo "==================================="
echo "  Reality - Always On Setup"
echo "==================================="
echo

# Prevent sleep
echo "[1/4] Configuring power settings (prevents sleep)..."
sudo pmset -a sleep 0
sudo pmset -a disksleep 0
sudo pmset -a displaysleep 10  # Screen off after 10 min, but system stays awake
echo "Done."
echo

# Copy service files
echo "[2/4] Installing service files..."
cp ~/reality/scripts/com.reality.alfred.plist ~/Library/LaunchAgents/
cp ~/reality/scripts/com.reality.zigbee2mqtt.plist ~/Library/LaunchAgents/
echo "Done."
echo

# Unload if already loaded (ignore errors)
echo "[3/4] Stopping any existing services..."
launchctl unload ~/Library/LaunchAgents/com.reality.alfred.plist 2>/dev/null || true
launchctl unload ~/Library/LaunchAgents/com.reality.zigbee2mqtt.plist 2>/dev/null || true
echo "Done."
echo

# Load services
echo "[4/4] Starting services..."
launchctl load ~/Library/LaunchAgents/com.reality.zigbee2mqtt.plist
sleep 3  # Give Zigbee2MQTT time to start before Alfred connects
launchctl load ~/Library/LaunchAgents/com.reality.alfred.plist
echo "Done."
echo

echo "==================================="
echo "  Reality is now always on!"
echo "==================================="
echo
echo "Services:"
echo "  - Zigbee2MQTT: running"
echo "  - Alfred: running"
echo
echo "Logs:"
echo "  tail -f /tmp/alfred.log"
echo "  tail -f /tmp/zigbee2mqtt.log"
echo
echo "Commands:"
echo "  launchctl stop com.reality.alfred      # Stop Alfred"
echo "  launchctl start com.reality.alfred     # Start Alfred"
echo "  launchctl stop com.reality.zigbee2mqtt # Stop Zigbee2MQTT"
echo "  launchctl start com.reality.zigbee2mqtt# Start Zigbee2MQTT"
echo
