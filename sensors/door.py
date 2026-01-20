"""
Door sensor handler via MQTT.
Subscribes to Zigbee2MQTT messages for the door sensor.
"""

import json
from typing import Callable, Optional

import paho.mqtt.client as mqtt

from config import config
from sensors.base import BaseSensor


class DoorSensor(BaseSensor):
    """
    Listens for door open/close events from Zigbee2MQTT.

    Zigbee2MQTT publishes messages like:
    {"contact": false, "linkquality": 255, ...}

    contact: true = door closed, false = door opened
    """

    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.callback: Optional[Callable[[dict], None]] = None
        self._running = False
        self._last_contact: Optional[bool] = None  # Track previous state

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        """Called when connected to MQTT broker."""
        print(f"[DoorSensor] Connected to MQTT broker at {config.MQTT_BROKER}:{config.MQTT_PORT}")
        client.subscribe(config.DOOR_SENSOR_TOPIC)
        print(f"[DoorSensor] Subscribed to {config.DOOR_SENSOR_TOPIC}")

    def _on_message(self, client, userdata, msg):
        """Called when a message is received."""
        try:
            payload = json.loads(msg.payload.decode())

            # Zigbee2MQTT contact sensors: contact=false means door opened
            if "contact" in payload:
                contact = payload["contact"]

                # Only trigger on state CHANGE from closed (True) to open (False)
                if self._last_contact is True and contact is False:
                    print(f"[DoorSensor] Door opened!")
                    if self.callback:
                        self.callback({
                            "event": "door_opened",
                            "raw": payload
                        })
                elif self._last_contact is False and contact is True:
                    print(f"[DoorSensor] Door closed")

                # Update last known state
                self._last_contact = contact

        except json.JSONDecodeError as e:
            print(f"[DoorSensor] Failed to parse message: {e}")
        except Exception as e:
            print(f"[DoorSensor] Error handling message: {e}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        """Called when disconnected from MQTT broker."""
        print(f"[DoorSensor] Disconnected from MQTT broker (reason: {reason_code})")

    def start(self, callback: Callable[[dict], None]) -> None:
        """Start listening for door events."""
        self.callback = callback

        # Create MQTT client (v2 API)
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        print(f"[DoorSensor] Connecting to {config.MQTT_BROKER}:{config.MQTT_PORT}...")
        self.client.connect(config.MQTT_BROKER, config.MQTT_PORT, 60)

        self._running = True
        self.client.loop_start()

    def stop(self) -> None:
        """Stop listening for door events."""
        self._running = False
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            print("[DoorSensor] Stopped")
