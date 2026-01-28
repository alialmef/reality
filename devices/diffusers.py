"""
Scent diffuser controller via Zigbee2MQTT.
Controls smart plugs connected to diffusers through MQTT commands.
"""

import json
import os
from typing import Optional, Dict

import paho.mqtt.client as mqtt

from config import config


def _load_device_config():
    """Load device configuration from config/devices.json."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "devices.json")
    try:
        with open(config_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[Diffusers] Warning: {config_path} not found, using empty config")
        return {"diffusers": {}}


# Load diffuser configuration from config/devices.json
_device_config = _load_device_config()
DIFFUSERS: Dict[str, dict] = _device_config.get("diffusers", {})


class DiffuserController:
    """
    Controls scent diffusers via Zigbee2MQTT smart plugs.
    Simple on/off control for each scent.
    """

    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self._connected = False
        self._states: Dict[str, bool] = {name: False for name in DIFFUSERS}
        self._connect()

    def _connect(self):
        """Connect to MQTT broker."""
        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.connect(config.MQTT_BROKER, config.MQTT_PORT, 60)
            self.client.loop_start()
        except Exception as e:
            print(f"[Diffusers] Failed to connect to MQTT: {e}")

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        """Called when connected to MQTT broker."""
        self._connected = True
        print(f"[Diffusers] Connected to MQTT broker")

        # Subscribe to state updates for all diffusers
        for name, diffuser in DIFFUSERS.items():
            topic = f"zigbee2mqtt/{diffuser['id']}"
            client.subscribe(topic)

    def _on_message(self, client, userdata, msg):
        """Called when a message is received - track state updates."""
        try:
            payload = json.loads(msg.payload.decode())

            # Find which diffuser this is for
            for name, diffuser in DIFFUSERS.items():
                if diffuser['id'] in msg.topic:
                    state = payload.get("state", "OFF") == "ON"
                    self._states[name] = state
                    break
        except Exception:
            pass

    def _publish(self, device_id: str, payload: dict) -> bool:
        """Publish a command to a diffuser."""
        if not self.client or not self._connected:
            print("[Diffusers] Not connected to MQTT")
            return False

        topic = f"zigbee2mqtt/{device_id}/set"
        try:
            self.client.publish(topic, json.dumps(payload))
            return True
        except Exception as e:
            print(f"[Diffusers] Failed to publish: {e}")
            return False

    def turn_on(self, scent: str) -> str:
        """Turn on a specific scent diffuser."""
        scent_lower = scent.lower()

        if scent_lower not in DIFFUSERS:
            available = ", ".join(DIFFUSERS.keys())
            return f"Unknown scent '{scent}'. Available: {available}"

        diffuser = DIFFUSERS[scent_lower]
        if self._publish(diffuser["id"], {"state": "ON"}):
            self._states[scent_lower] = True
            return f"{diffuser['name']} is now on. {diffuser['description']}"
        return f"Failed to turn on {diffuser['name']}"

    def turn_off(self, scent: str) -> str:
        """Turn off a specific scent diffuser."""
        scent_lower = scent.lower()

        if scent_lower not in DIFFUSERS:
            available = ", ".join(DIFFUSERS.keys())
            return f"Unknown scent '{scent}'. Available: {available}"

        diffuser = DIFFUSERS[scent_lower]
        if self._publish(diffuser["id"], {"state": "OFF"}):
            self._states[scent_lower] = False
            return f"{diffuser['name']} is now off"
        return f"Failed to turn off {diffuser['name']}"

    def turn_all_on(self) -> str:
        """Turn on all diffusers."""
        results = []
        for scent in DIFFUSERS:
            result = self.turn_on(scent)
            results.append(result)
        return " ".join(results)

    def turn_all_off(self) -> str:
        """Turn off all diffusers."""
        results = []
        for scent in DIFFUSERS:
            result = self.turn_off(scent)
            results.append(result)
        return "All diffusers off"

    def get_status(self) -> str:
        """Get the current status of all diffusers."""
        lines = ["Diffuser status:"]
        for scent, diffuser in DIFFUSERS.items():
            state = "on" if self._states.get(scent, False) else "off"
            lines.append(f"  - {diffuser['name']}: {state}")
        return "\n".join(lines)

    def get_scent_info(self, scent: str) -> str:
        """Get information about a specific scent."""
        scent_lower = scent.lower()

        if scent_lower not in DIFFUSERS:
            available = ", ".join(DIFFUSERS.keys())
            return f"Unknown scent '{scent}'. Available: {available}"

        diffuser = DIFFUSERS[scent_lower]
        state = "on" if self._states.get(scent_lower, False) else "off"
        return f"{diffuser['name']} ({state}): {diffuser['description']}"


# Singleton instance
_controller = None


def get_diffuser_controller() -> DiffuserController:
    """Get the diffuser controller singleton."""
    global _controller
    if _controller is None:
        _controller = DiffuserController()
    return _controller
