# Alfred

A warm presence at your door. When you come home, Alfred greets you — naturally, warmly, like a companion who knows you.

## What This Does

1. Door sensor detects when you arrive home
2. Context is gathered (time of day, how long you've been gone, weather)
3. Claude generates a greeting in Alfred's voice
4. ElevenLabs speaks it through your speaker

The whole thing takes about 2-3 seconds from door opening to hearing Alfred's voice.

## Hardware Required

- **Zigbee door sensor** (ThirdReality Zigbee Contact Sensor recommended)
- **Zigbee USB coordinator** (Sonoff Zigbee 3.0 USB Dongle Plus-E)
- **Computer** that's always on (Mac Mini, Minisforum, Raspberry Pi 5)
- **Speaker** near your entrance (any Bluetooth or wired speaker)

## Software Required

- **Zigbee2MQTT** - bridges Zigbee devices to MQTT
- **Mosquitto** - MQTT message broker
- Python 3.10+

## Setup

### 1. Install Mosquitto (MQTT Broker)

**macOS:**
```bash
brew install mosquitto
brew services start mosquitto
```

**Linux:**
```bash
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

### 2. Install Zigbee2MQTT

Follow the official guide: https://www.zigbee2mqtt.io/guide/installation/

**Quick version for macOS/Linux:**

```bash
# Clone Zigbee2MQTT
git clone https://github.com/Koenkk/zigbee2mqtt.git
cd zigbee2mqtt

# Install dependencies
npm ci

# Create config
cp data/configuration.example.yaml data/configuration.yaml
```

Edit `data/configuration.yaml`:
```yaml
homeassistant: false
permit_join: true
mqtt:
  base_topic: zigbee2mqtt
  server: mqtt://localhost
serial:
  port: /dev/tty.usbserial-XXX  # Find your dongle's port
frontend:
  port: 8080
```

To find your dongle's port:
```bash
ls /dev/tty.usb*   # macOS
ls /dev/ttyUSB*    # Linux
```

Start Zigbee2MQTT:
```bash
npm start
```

### 3. Pair Your Door Sensor

1. Open http://localhost:8080 (Zigbee2MQTT dashboard)
2. Click "Permit join" to allow new devices
3. Put your door sensor in pairing mode (usually hold button for 5 seconds)
4. It should appear in the dashboard
5. Note the device name (e.g., `front_door`)

### 4. Set Up Alfred

```bash
cd /path/to/alfred

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create config
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# MQTT
MQTT_BROKER=localhost
MQTT_PORT=1883
DOOR_SENSOR_TOPIC=zigbee2mqtt/front_door  # Match your device name

# Get from https://console.anthropic.com
ANTHROPIC_API_KEY=sk-ant-...

# Get from https://elevenlabs.io
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...  # Find a voice you like in their voice library

# Optional
OPENWEATHER_API_KEY=...
OPENWEATHER_CITY=San Francisco
```

### 5. Find an ElevenLabs Voice

1. Go to https://elevenlabs.io/voice-library
2. Search for British male voices
3. Find one that sounds warm and measured (good for Alfred)
4. Copy the Voice ID from the voice page
5. Add it to your `.env`

Recommended voices to try:
- "Daniel" - British, warm, measured
- "George" - British, authoritative but kind
- Or clone your own

### 6. Run Alfred

```bash
python main.py
```

You should see:
```
==================================================
  ALFRED
  A warm presence at your door
==================================================

[Alfred] Initializing components...
[DoorSensor] Connecting to localhost:1883...
[DoorSensor] Connected to MQTT broker
[DoorSensor] Subscribed to zigbee2mqtt/front_door
[Speaker] Initialized audio output
[Alfred] All components initialized

[Alfred] Listening for arrivals. Press Ctrl+C to stop.
```

Open your front door. Alfred should greet you.

## Testing Without Hardware

You can simulate a door open event:

```bash
# In another terminal
mosquitto_pub -t "zigbee2mqtt/front_door" -m '{"contact": false}'
```

## Running as a Service

To keep Alfred running after you close the terminal:

**macOS (launchd):**

Create `~/Library/LaunchAgents/com.alfred.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.alfred</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/alfred/venv/bin/python</string>
        <string>/path/to/alfred/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/alfred</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Then:
```bash
launchctl load ~/Library/LaunchAgents/com.alfred.plist
```

**Linux (systemd):**

Create `/etc/systemd/system/alfred.service`:
```ini
[Unit]
Description=Alfred - Door Greeter
After=network.target mosquitto.service

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/alfred
ExecStart=/path/to/alfred/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable alfred
sudo systemctl start alfred
```

## Troubleshooting

**"Failed to connect to MQTT broker"**
- Is Mosquitto running? `brew services list` (macOS) or `systemctl status mosquitto` (Linux)

**"No door events received"**
- Check Zigbee2MQTT dashboard - is the sensor online?
- Check the MQTT topic matches your sensor name
- Test with: `mosquitto_sub -t "zigbee2mqtt/#" -v`

**"Failed to generate greeting"**
- Check your Anthropic API key
- Check you have credits

**"Failed to synthesize speech"**
- Check your ElevenLabs API key
- Check the Voice ID is correct

**"No audio plays"**
- Check your speaker is connected and selected as output
- Try playing a test sound: `afplay /System/Library/Sounds/Ping.aiff` (macOS)

## What's Next

This is v1. Future additions:

- [ ] Continuous voice (always-on listening)
- [ ] More rooms, more sensors
- [ ] Calendar integration
- [ ] Learning patterns over time
- [ ] Multiple people recognition
- [ ] Local LLM option
