#!/bin/bash
# Uninstall Reality services

echo "Stopping and removing Reality services..."

launchctl unload ~/Library/LaunchAgents/com.reality.alfred.plist 2>/dev/null || true
launchctl unload ~/Library/LaunchAgents/com.reality.zigbee2mqtt.plist 2>/dev/null || true

rm -f ~/Library/LaunchAgents/com.reality.alfred.plist
rm -f ~/Library/LaunchAgents/com.reality.zigbee2mqtt.plist

echo "Done. Services removed."
