"""
Text-to-speech using ElevenLabs.
"""

import io
import requests
from typing import Optional

from config import config


class TextToSpeech:
    """ElevenLabs TTS integration."""

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self):
        if not config.ELEVENLABS_API_KEY:
            raise ValueError("ELEVENLABS_API_KEY not configured")
        if not config.ELEVENLABS_VOICE_ID:
            raise ValueError("ELEVENLABS_VOICE_ID not configured")

        self.api_key = config.ELEVENLABS_API_KEY
        self.voice_id = config.ELEVENLABS_VOICE_ID

    def synthesize(self, text: str) -> Optional[bytes]:
        """
        Convert text to speech.

        Args:
            text: The text to speak.

        Returns:
            MP3 audio bytes, or None on error.
        """
        try:
            print(f"[TTS] Synthesizing: {text}")

            response = requests.post(
                f"{self.BASE_URL}/text-to-speech/{self.voice_id}",
                headers={
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": self.api_key,
                },
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",  # Slower, more deliberate
                    "voice_settings": {
                        "stability": 0.90,        # Very steady
                        "similarity_boost": 0.80,  # Match original voice closely
                        "style": 0.0,              # No exaggeration, natural delivery
                        "use_speaker_boost": True,
                    },
                },
                timeout=10,
            )
            response.raise_for_status()

            print(f"[TTS] Synthesized {len(response.content)} bytes of audio")
            return response.content

        except Exception as e:
            print(f"[TTS] Error synthesizing speech: {e}")
            return None
