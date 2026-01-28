"""
Light controller via Zigbee2MQTT.
Controls smart bulbs through MQTT commands.
"""

import json
import os
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import paho.mqtt.client as mqtt

from config import config


def _load_device_config():
    """Load device configuration from config/devices.json."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "devices.json")
    try:
        with open(config_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[Lights] Warning: {config_path} not found, using empty config")
        return {"lights": {}, "rooms": {}}

# Delay between commands to different lights (Zigbee mesh needs time)
COMMAND_DELAY = 0.15  # 150ms between commands


@dataclass
class Light:
    """Represents a smart light."""
    id: str  # Zigbee device ID
    name: str  # Friendly name
    location: str  # Room/area
    state: bool = False  # On/off
    brightness: int = 254  # 0-254
    color_temp: int = 300  # 154 (cool) to 500 (warm)
    hue: int = 0  # 0-360
    saturation: int = 0  # 0-100


# Named colors mapped to hue/saturation
COLORS: Dict[str, tuple] = {
    "red": (0, 100),
    "orange": (30, 100),
    "yellow": (55, 100),
    "green": (120, 100),
    "cyan": (180, 100),
    "blue": (240, 100),
    "purple": (270, 100),
    "pink": (320, 100),
    "magenta": (300, 100),
    "white": (0, 0),  # No saturation = white
}


# Load device configuration
_device_config = _load_device_config()

# Light configuration - loaded from config/devices.json
LIGHTS: Dict[str, Light] = {
    name: Light(
        id=data["id"],
        name=data["name"],
        location=data["location"]
    )
    for name, data in _device_config.get("lights", {}).items()
}

# Room groupings - loaded from config/devices.json
ROOMS: Dict[str, List[str]] = _device_config.get("rooms", {})


class LightController:
    """Controls smart lights via Zigbee2MQTT."""

    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self._connected = False
        # Track actual light states from Zigbee2MQTT
        self._light_states: Dict[str, Dict] = {}
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
            print(f"[Lights] Failed to connect to MQTT: {e}")

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        """Called when connected to MQTT broker."""
        self._connected = True
        print(f"[Lights] Connected to MQTT broker")
        # Subscribe to state updates for all lights
        for light in LIGHTS.values():
            topic = f"zigbee2mqtt/{light.id}"
            client.subscribe(topic)
            # Request current state
            client.publish(f"zigbee2mqtt/{light.id}/get", '{"state": ""}')
        print(f"[Lights] Subscribed to {len(LIGHTS)} light state topics")

    def _on_message(self, client, userdata, msg):
        """Handle incoming light state updates."""
        try:
            # Extract device ID from topic (zigbee2mqtt/0x...)
            topic_parts = msg.topic.split('/')
            if len(topic_parts) < 2:
                return
            device_id = topic_parts[1]

            # Parse state
            payload = json.loads(msg.payload.decode())
            self._light_states[device_id] = payload

            # Update our Light objects
            for light in LIGHTS.values():
                if light.id == device_id:
                    old_state = light.state
                    light.state = payload.get("state", "OFF") == "ON"
                    light.brightness = payload.get("brightness", 254)
                    if "color" in payload:
                        light.hue = payload["color"].get("hue", 0)
                        light.saturation = payload["color"].get("saturation", 0)
                    if "color_temp" in payload:
                        light.color_temp = payload["color_temp"]
                    # Log state changes
                    if old_state != light.state:
                        print(f"[Lights] {light.location} now {'on' if light.state else 'off'}")
        except Exception as e:
            print(f"[Lights] Error parsing state: {e}")

    def _publish(self, device_id: str, payload: Dict[str, Any]) -> bool:
        """Publish a command to a light."""
        if not self._connected or not self.client:
            print("[Lights] Not connected to MQTT")
            return False

        topic = f"zigbee2mqtt/{device_id}/set"
        try:
            self.client.publish(topic, json.dumps(payload))
            return True
        except Exception as e:
            print(f"[Lights] Failed to publish: {e}")
            return False

    def _get_light(self, name: str) -> Optional[Light]:
        """Get a light by name, with fuzzy matching."""
        # Exact match
        if name in LIGHTS:
            return LIGHTS[name]

        # Try to match by location or partial name
        name_lower = name.lower()
        for light_name, light in LIGHTS.items():
            if name_lower in light_name.lower() or name_lower in light.location.lower():
                return light

        return None

    def _get_room_lights(self, room: str) -> List[Light]:
        """Get all lights in a room."""
        room_lower = room.lower()
        for room_name, light_names in ROOMS.items():
            if room_lower in room_name.lower():
                return [LIGHTS[name] for name in light_names]
        return []

    # === Public API ===

    def turn_on(self, target: str, brightness: int = None) -> str:
        """
        Turn on a light or room.

        Args:
            target: Light name or room name
            brightness: Optional brightness 0-100

        Returns:
            Status message
        """
        # Check if it's a room
        room_lights = self._get_room_lights(target)
        if room_lights:
            payload = {"state": "ON"}
            if brightness is not None:
                payload["brightness"] = int(brightness * 2.54)  # Convert 0-100 to 0-254

            for light in room_lights:
                self._publish(light.id, payload)
                # Update local state immediately
                light.state = True
                if brightness:
                    light.brightness = payload["brightness"]
                time.sleep(COMMAND_DELAY)

            print(f"[Lights] Turned on {target}")
            return f"Turned on {len(room_lights)} lights in the {target}"

        # Single light
        light = self._get_light(target)
        if not light:
            return f"I don't know a light called '{target}'"

        payload = {"state": "ON"}
        if brightness is not None:
            payload["brightness"] = int(brightness * 2.54)

        self._publish(light.id, payload)
        # Update local state immediately
        light.state = True
        if brightness:
            light.brightness = payload["brightness"]

        print(f"[Lights] Turned on {light.location}")
        return f"Turned on the {light.location} light"

    def turn_off(self, target: str) -> str:
        """
        Turn off a light or room.

        Args:
            target: Light name or room name

        Returns:
            Status message
        """
        # Check if it's a room
        room_lights = self._get_room_lights(target)
        if room_lights:
            for light in room_lights:
                self._publish(light.id, {"state": "OFF"})
                light.state = False
                time.sleep(COMMAND_DELAY)

            return f"Turned off the {target} lights"

        # Single light
        light = self._get_light(target)
        if not light:
            return f"I don't know a light called '{target}'"

        self._publish(light.id, {"state": "OFF"})
        light.state = False

        return f"Turned off the {light.location} light"

    def set_brightness(self, target: str, brightness: int) -> str:
        """
        Set brightness for a light or room (0-100).

        Args:
            target: Light name or room name
            brightness: 0-100

        Returns:
            Status message
        """
        brightness = max(0, min(100, brightness))  # Clamp to 0-100
        zigbee_brightness = int(brightness * 2.54)  # Convert to 0-254

        # Check if it's a room
        room_lights = self._get_room_lights(target)
        if room_lights:
            for light in room_lights:
                self._publish(light.id, {"state": "ON", "brightness": zigbee_brightness})
                light.brightness = zigbee_brightness
                light.state = True
                time.sleep(COMMAND_DELAY)

            return f"Set {target} lights to {brightness}%"

        # Single light
        light = self._get_light(target)
        if not light:
            return f"I don't know a light called '{target}'"

        self._publish(light.id, {"state": "ON", "brightness": zigbee_brightness})
        light.brightness = zigbee_brightness

        return f"Set the {light.location} light to {brightness}%"

    def turn_all_on(self, brightness: int = None) -> str:
        """Turn on all lights."""
        payload = {"state": "ON"}
        if brightness is not None:
            payload["brightness"] = int(brightness * 2.54)

        for light in LIGHTS.values():
            self._publish(light.id, payload)
            light.state = True
            time.sleep(COMMAND_DELAY)

        return "Turned on all lights"

    def turn_all_off(self) -> str:
        """Turn off all lights."""
        for light in LIGHTS.values():
            self._publish(light.id, {"state": "OFF"})
            light.state = False
            time.sleep(COMMAND_DELAY)

        return "Turned off all lights"

    def set_all_color(self, color: str) -> str:
        """Set color for ALL lights with delays between commands."""
        color_lower = color.lower()
        if color_lower not in COLORS:
            available = ", ".join(COLORS.keys())
            return f"I don't know that color. Try: {available}"

        hue, saturation = COLORS[color_lower]
        payload = {"state": "ON", "color": {"hue": hue, "saturation": saturation}}

        for light in LIGHTS.values():
            self._publish(light.id, payload)
            light.hue = hue
            light.saturation = saturation
            light.state = True
            time.sleep(COMMAND_DELAY)

        print(f"[Lights] Set all to {color}")
        return f"Set all lights to {color}"

    def set_all_brightness(self, brightness: int) -> str:
        """Set brightness for ALL lights with delays between commands."""
        brightness = max(0, min(100, brightness))
        zigbee_brightness = int(brightness * 2.54)
        payload = {"state": "ON", "brightness": zigbee_brightness}

        for light in LIGHTS.values():
            self._publish(light.id, payload)
            light.brightness = zigbee_brightness
            light.state = True
            time.sleep(COMMAND_DELAY)

        print(f"[Lights] Set all to {brightness}%")
        return f"Set all lights to {brightness}%"

    def set_all_color_temp(self, warmth: str) -> str:
        """Set color temperature for ALL lights with delays between commands."""
        warmth_lower = warmth.lower()
        if warmth_lower in ("cool", "cold", "daylight"):
            color_temp = 154
            desc = "cool white"
        elif warmth_lower in ("warm", "cozy", "soft"):
            color_temp = 500
            desc = "warm white"
        elif warmth_lower in ("neutral", "natural", "normal"):
            color_temp = 300
            desc = "neutral white"
        else:
            try:
                value = int(warmth)
                value = max(0, min(100, value))
                color_temp = 154 + int(value * 3.46)
                desc = f"{value}% warm"
            except ValueError:
                return "I didn't understand that. Try 'warm', 'cool', or a number 0-100."

        payload = {"state": "ON", "color_temp": color_temp}

        for light in LIGHTS.values():
            self._publish(light.id, payload)
            light.color_temp = color_temp
            light.state = True
            time.sleep(COMMAND_DELAY)

        print(f"[Lights] Set all to {desc}")
        return f"Set all lights to {desc}"

    def get_status(self) -> str:
        """Get a summary of all lights."""
        on_lights = [l for l in LIGHTS.values() if l.state]
        off_lights = [l for l in LIGHTS.values() if not l.state]

        if not on_lights:
            return "All lights are off"
        elif not off_lights:
            return "All lights are on"
        else:
            on_locations = [l.location for l in on_lights]
            return f"Lights on in: {', '.join(on_locations)}"

    def get_detailed_status(self) -> str:
        """Get detailed status of all lights for Alfred's awareness."""
        lines = []
        for name, light in LIGHTS.items():
            state = "on" if light.state else "off"
            brightness_pct = int(light.brightness / 2.54)

            # Determine color description
            color_desc = self._describe_color(light)

            lines.append(f"- {light.location}: {state}, {brightness_pct}% brightness, {color_desc}")

        return "\n".join(lines)

    def _describe_color(self, light: Light) -> str:
        """Get a human-readable color description."""
        # If low saturation, it's white with color temp
        if light.saturation < 20:
            if light.color_temp < 200:
                return "cool white"
            elif light.color_temp > 400:
                return "warm white"
            else:
                return "neutral white"

        # Find closest named color by hue
        hue = light.hue
        if hue < 15 or hue >= 345:
            return "red"
        elif hue < 45:
            return "orange"
        elif hue < 70:
            return "yellow"
        elif hue < 150:
            return "green"
        elif hue < 210:
            return "cyan"
        elif hue < 270:
            return "blue"
        elif hue < 330:
            return "purple"
        else:
            return "pink"

    def get_light_context(self) -> str:
        """Get light status formatted for Alfred's context."""
        return f"""Current light states:
{self.get_detailed_status()}

You control these lights. You know their current state."""

    def get_available_lights(self) -> List[str]:
        """Get list of available light names."""
        return list(LIGHTS.keys())

    def get_available_rooms(self) -> List[str]:
        """Get list of rooms with lights."""
        return list(ROOMS.keys())

    def set_color(self, target: str, color: str) -> str:
        """
        Set color for a light or room by name.

        Args:
            target: Light name or room name
            color: Color name (red, blue, green, etc.) or "white"

        Returns:
            Status message
        """
        color_lower = color.lower()
        if color_lower not in COLORS:
            available = ", ".join(COLORS.keys())
            return f"I don't know that color. Try: {available}"

        hue, saturation = COLORS[color_lower]
        payload = {"state": "ON", "color": {"hue": hue, "saturation": saturation}}

        # Check if it's a room
        room_lights = self._get_room_lights(target)
        if room_lights:
            for light in room_lights:
                self._publish(light.id, payload)
                # Update local state
                light.hue = hue
                light.saturation = saturation
                light.state = True  # Setting color turns light on
                time.sleep(COMMAND_DELAY)
            print(f"[Lights] Set {target} to {color}")
            return f"Set {target} lights to {color}"

        # Single light
        light = self._get_light(target)
        if not light:
            return f"I don't know a light called '{target}'"

        self._publish(light.id, payload)
        # Update local state
        light.hue = hue
        light.saturation = saturation
        light.state = True
        print(f"[Lights] Set {light.location} to {color}")
        return f"Set the {light.location} light to {color}"

    def set_color_temp(self, target: str, warmth: str) -> str:
        """
        Set color temperature (warm/cool white).

        Args:
            target: Light name or room name
            warmth: "warm", "cool", "neutral", or a value 0-100 (0=cool, 100=warm)

        Returns:
            Status message
        """
        # Map warmth descriptions to color temp values
        # Zigbee: 154 = cool (6500K), 500 = warm (2000K)
        warmth_lower = warmth.lower()
        if warmth_lower in ("cool", "cold", "daylight"):
            color_temp = 154
            desc = "cool white"
        elif warmth_lower in ("warm", "cozy", "soft"):
            color_temp = 500
            desc = "warm white"
        elif warmth_lower in ("neutral", "natural", "normal"):
            color_temp = 300
            desc = "neutral white"
        else:
            # Try to parse as number (0-100 scale)
            try:
                value = int(warmth)
                value = max(0, min(100, value))
                # Map 0-100 to 154-500
                color_temp = 154 + int(value * 3.46)
                desc = f"{value}% warm"
            except ValueError:
                return "I didn't understand that. Try 'warm', 'cool', or a number 0-100."

        payload = {"state": "ON", "color_temp": color_temp}

        # Check if it's a room
        room_lights = self._get_room_lights(target)
        if room_lights:
            for light in room_lights:
                self._publish(light.id, payload)
                light.color_temp = color_temp
                light.state = True
                time.sleep(COMMAND_DELAY)
            return f"Set {target} lights to {desc}"

        # Single light
        light = self._get_light(target)
        if not light:
            return f"I don't know a light called '{target}'"

        self._publish(light.id, payload)
        light.color_temp = color_temp
        return f"Set the {light.location} light to {desc}"

    def get_available_colors(self) -> List[str]:
        """Get list of available color names."""
        return list(COLORS.keys())


# Singleton instance
_controller: Optional[LightController] = None


def get_light_controller() -> LightController:
    """Get the singleton light controller instance."""
    global _controller
    if _controller is None:
        _controller = LightController()
    return _controller
