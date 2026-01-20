"""
Configuration management for Alfred.
Loads settings from environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # MQTT
    MQTT_BROKER: str = os.getenv("MQTT_BROKER", "localhost")
    MQTT_PORT: int = int(os.getenv("MQTT_PORT", "1883"))
    DOOR_SENSOR_TOPIC: str = os.getenv("DOOR_SENSOR_TOPIC", "zigbee2mqtt/front_door")

    # Anthropic
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # OpenAI (for Whisper STT)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # ElevenLabs
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "")

    # Weather (optional)
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
    OPENWEATHER_CITY: str = os.getenv("OPENWEATHER_CITY", "San Francisco")

    # Presence tracking
    MIN_ABSENCE_SECONDS: int = 0  # TESTING: greet every time (normally 300 = 5 minutes)


config = Config()
