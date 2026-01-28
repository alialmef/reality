"""
Coffee maker controller via Zigbee2MQTT.
Controls a smart plug connected to the coffee maker.
"""

import json
import os
from typing import Optional

import paho.mqtt.client as mqtt

from config import config


def _load_device_config():
    """Load device configuration from config/devices.json."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "devices.json")
    try:
        with open(config_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[Coffee] Warning: {config_path} not found, using empty config")
        return {"coffee_maker": {"id": "", "name": "Coffee Maker"}}


# Load coffee maker configuration from config/devices.json
_device_config = _load_device_config()
COFFEE_MAKER = _device_config.get("coffee_maker", {"id": "", "name": "Coffee Maker"})


class CoffeeController:
    """
    Controls the coffee maker via a Zigbee2MQTT smart plug.
    Simple on/off control - turning on starts brewing.
    """

    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self._connected = False
        self._state = False
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
            print(f"[Coffee] Failed to connect to MQTT: {e}")

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        """Called when connected to MQTT broker."""
        self._connected = True
        print(f"[Coffee] Connected to MQTT broker")

        # Subscribe to state updates
        topic = f"zigbee2mqtt/{COFFEE_MAKER['id']}"
        client.subscribe(topic)

    def _on_message(self, client, userdata, msg):
        """Called when a message is received - track state updates."""
        try:
            payload = json.loads(msg.payload.decode())
            if COFFEE_MAKER['id'] in msg.topic:
                self._state = payload.get("state", "OFF") == "ON"
        except Exception:
            pass

    def _publish(self, payload: dict) -> bool:
        """Publish a command to the coffee maker plug."""
        if not self.client or not self._connected:
            print("[Coffee] Not connected to MQTT")
            return False

        topic = f"zigbee2mqtt/{COFFEE_MAKER['id']}/set"
        try:
            self.client.publish(topic, json.dumps(payload))
            return True
        except Exception as e:
            print(f"[Coffee] Failed to publish: {e}")
            return False

    def brew(self) -> str:
        """Start brewing coffee."""
        if self._publish({"state": "ON"}):
            self._state = True
            return "Coffee maker on. Brewing now, sir."
        return "Failed to start the coffee maker"

    def turn_off(self) -> str:
        """Turn off the coffee maker."""
        if self._publish({"state": "OFF"}):
            self._state = False
            return "Coffee maker off"
        return "Failed to turn off the coffee maker"

    def get_status(self) -> str:
        """Get the current status of the coffee maker."""
        state = "brewing" if self._state else "off"
        return f"Coffee maker is {state}"

    def is_brewing(self) -> bool:
        """Check if coffee is currently brewing."""
        return self._state


# Singleton instance
_controller = None


def get_coffee_controller() -> CoffeeController:
    """Get the coffee controller singleton."""
    global _controller
    if _controller is None:
        _controller = CoffeeController()
    return _controller
