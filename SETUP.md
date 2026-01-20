# Alfred Setup Guide

Complete setup instructions for deploying Alfred on a new Mac Mini (or any always-on Mac).

---

## Prerequisites

Before starting, ensure you have:

1. **Mac Mini** (or any Mac) that will stay on
2. **Zigbee USB Coordinator** - Sonoff Zigbee 3.0 USB Dongle Plus V2 (plugged into the Mac)
3. **Zigbee Door Sensor** - ThirdReality 3RDS17BZ or similar
4. **Speaker** - Connected to the Mac (Bluetooth or wired)
5. **API Keys** (you should already have these):
   - Anthropic API key
   - ElevenLabs API key and Voice ID

---

## Step 1: Install Homebrew (if not installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the post-install instructions to add Homebrew to your PATH.

---

## Step 2: Install System Dependencies

```bash
# Install Mosquitto (MQTT broker)
brew install mosquitto

# Start Mosquitto as a background service
brew services start mosquitto

# Install Node.js (for Zigbee2MQTT)
brew install node

# Install pnpm (required by Zigbee2MQTT)
npm install -g pnpm
```

---

## Step 3: Install Zigbee2MQTT

```bash
# Clone Zigbee2MQTT to home directory
cd ~
git clone --depth 1 https://github.com/Koenkk/zigbee2mqtt.git
cd zigbee2mqtt

# Install dependencies
npm install
```

---

## Step 4: Find Your Zigbee USB Dongle

Plug in the Zigbee USB coordinator and find its port:

```bash
ls /dev/tty.usb*
```

You should see something like `/dev/tty.usbserial-10`. Note this path.

To confirm it's the Sonoff dongle:

```bash
system_profiler SPUSBDataType | grep -A 10 "Sonoff"
```

---

## Step 5: Configure Zigbee2MQTT

Create the configuration file:

```bash
cat > ~/zigbee2mqtt/data/configuration.yaml << 'EOF'
homeassistant:
  enabled: false
mqtt:
  base_topic: zigbee2mqtt
  server: mqtt://localhost
serial:
  port: /dev/tty.usbserial-10
  adapter: ezsp
frontend:
  enabled: true
  port: 8080
advanced:
  log_level: info
permit_join: true
EOF
```

**Important:** Replace `/dev/tty.usbserial-10` with your actual dongle path from Step 4.

---

## Step 6: Start Zigbee2MQTT and Pair the Door Sensor

Start Zigbee2MQTT:

```bash
cd ~/zigbee2mqtt
npm start
```

In a browser, open: http://localhost:8080

**Pair your door sensor:**
1. In the Zigbee2MQTT dashboard, ensure "Permit join" is enabled
2. On the door sensor, hold the button for 5+ seconds until LED flashes
3. Wait for it to appear in the dashboard (usually within 30 seconds)
4. Note the device name (e.g., `0xb40e060fffe11fc5`)

**Rename the sensor to `front_door`:**

```bash
mosquitto_pub -t "zigbee2mqtt/bridge/request/device/rename" \
  -m '{"from": "0xb40e060fffe11fc5", "to": "front_door"}'
```

Replace the hex address with your actual device name.

Stop Zigbee2MQTT (Ctrl+C) for now. We'll run it as a service later.

---

## Step 7: Clone and Set Up Alfred

```bash
# Clone the repo (adjust URL as needed)
cd ~/Sites  # or wherever you want it
git clone <your-alfred-repo-url> alfred
cd alfred

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

---

## Step 8: Configure Alfred

Copy the example config and edit it:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```bash
# MQTT Configuration
MQTT_BROKER=localhost
MQTT_PORT=1883

# Zigbee2MQTT topic for your door sensor
DOOR_SENSOR_TOPIC=zigbee2mqtt/front_door

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE

# ElevenLabs API
ELEVENLABS_API_KEY=sk_YOUR_KEY_HERE
ELEVENLABS_VOICE_ID=YOUR_VOICE_ID_HERE

# Weather API (optional)
OPENWEATHER_API_KEY=
OPENWEATHER_CITY=
```

---

## Step 9: Test Alfred

With Zigbee2MQTT running in one terminal:

```bash
cd ~/zigbee2mqtt && npm start
```

In another terminal, start Alfred:

```bash
cd ~/Sites/alfred
source venv/bin/activate
python main.py
```

You should see:
```
==================================================
  ALFRED
  A warm presence at your door
==================================================

[Alfred] Initializing components...
[Speaker] Initialized audio output
[Alfred] All components initialized

[Alfred] Starting door sensor...
[DoorSensor] Connecting to localhost:1883...
[Alfred] Listening for arrivals. Press Ctrl+C to stop.

[DoorSensor] Connected to MQTT broker at localhost:1883
[DoorSensor] Subscribed to zigbee2mqtt/front_door
```

**Test with your door or simulate:**

```bash
# Simulate door close then open
mosquitto_pub -t "zigbee2mqtt/front_door" -m '{"contact": true}'
sleep 1
mosquitto_pub -t "zigbee2mqtt/front_door" -m '{"contact": false}'
```

You should hear Alfred greet you.

---

## Step 10: Set Up as Background Services

### 10a: Zigbee2MQTT Service

Create the launchd plist:

```bash
cat > ~/Library/LaunchAgents/com.zigbee2mqtt.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.zigbee2mqtt</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/npm</string>
        <string>start</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/zigbee2mqtt</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/zigbee2mqtt.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/zigbee2mqtt.err</string>
</dict>
</plist>
EOF
```

**Replace `YOUR_USERNAME` with your actual username.**

Load the service:

```bash
launchctl load ~/Library/LaunchAgents/com.zigbee2mqtt.plist
```

### 10b: Alfred Service

Create the launchd plist:

```bash
cat > ~/Library/LaunchAgents/com.alfred.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.alfred</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR_USERNAME/Sites/alfred/venv/bin/python</string>
        <string>/Users/YOUR_USERNAME/Sites/alfred/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/Sites/alfred</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/alfred.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/alfred.err</string>
</dict>
</plist>
EOF
```

**Replace `YOUR_USERNAME` with your actual username.**

Load the service:

```bash
launchctl load ~/Library/LaunchAgents/com.alfred.plist
```

---

## Step 11: Verify Services Are Running

```bash
# Check Mosquitto
brew services list | grep mosquitto

# Check Zigbee2MQTT
launchctl list | grep zigbee2mqtt
tail -20 /tmp/zigbee2mqtt.log

# Check Alfred
launchctl list | grep alfred
tail -20 /tmp/alfred.log
```

---

## Troubleshooting

### "Failed to connect to MQTT broker"
```bash
# Is Mosquitto running?
brew services list
brew services restart mosquitto
```

### "No door events received"
```bash
# Check Zigbee2MQTT dashboard
open http://localhost:8080

# Monitor MQTT messages
mosquitto_sub -t "zigbee2mqtt/#" -v
```

### "Failed to generate greeting"
- Check Anthropic API key in `.env`
- Check you have API credits

### "Failed to synthesize speech"
- Check ElevenLabs API key in `.env`
- Check Voice ID is correct

### "No audio plays"
```bash
# Test Mac audio
afplay /System/Library/Sounds/Ping.aiff

# Check audio output device
system_preferences # Audio settings
```

### Service not starting
```bash
# Check logs
tail -50 /tmp/alfred.err
tail -50 /tmp/zigbee2mqtt.err

# Unload and reload
launchctl unload ~/Library/LaunchAgents/com.alfred.plist
launchctl load ~/Library/LaunchAgents/com.alfred.plist
```

---

## How It Works

### Arrival Detection
- Door opens after you've been away → Alfred greets you

### Departure Detection
- Door opens within 10 minutes of arriving → Detected as leaving, no greeting

### Greeting Style
- "Welcome home, sir" / "Hello sir" / "Welcome back, sir" + one short addition
- Varies naturally each time
- Adapts to time of day and how long you've been away

---

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point, orchestrates everything |
| `personality/alfred.py` | System prompt defining the voice |
| `voice/tts.py` | ElevenLabs settings (speed, stability) |
| `context/gatherer.py` | Detects arriving vs leaving |
| `sensors/door.py` | MQTT door sensor listener |
| `.env` | API keys and configuration |

---

## Customization

### Change the personality
Edit `personality/alfred.py` - the `ALFRED_SYSTEM_PROMPT` defines how it speaks.

### Adjust voice settings
Edit `voice/tts.py` - the `voice_settings` dict controls:
- `stability`: 0.0-1.0 (higher = steadier)
- `similarity_boost`: 0.0-1.0 (match to original voice)
- `style`: 0.0-1.0 (style exaggeration)

### Change departure detection timing
Edit `context/gatherer.py` - the `600` value (seconds) is how long after arrival before a door open is considered leaving.

---

## Service Management Commands

```bash
# Stop Alfred
launchctl unload ~/Library/LaunchAgents/com.alfred.plist

# Start Alfred
launchctl load ~/Library/LaunchAgents/com.alfred.plist

# Stop Zigbee2MQTT
launchctl unload ~/Library/LaunchAgents/com.zigbee2mqtt.plist

# Start Zigbee2MQTT
launchctl load ~/Library/LaunchAgents/com.zigbee2mqtt.plist

# Stop Mosquitto
brew services stop mosquitto

# Start Mosquitto
brew services start mosquitto

# View Alfred logs
tail -f /tmp/alfred.log

# View Zigbee2MQTT logs
tail -f /tmp/zigbee2mqtt.log
```

---

## Quick Start Summary

1. `brew install mosquitto && brew services start mosquitto`
2. `brew install node && npm install -g pnpm`
3. Clone and install Zigbee2MQTT
4. Configure Zigbee2MQTT with your USB dongle path
5. Pair door sensor, rename to `front_door`
6. Clone Alfred repo
7. `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
8. Copy `.env.example` to `.env` and add API keys
9. Test with `python main.py`
10. Set up launchd services for always-on operation

---

You're done. When you walk through your door, your home will greet you.
