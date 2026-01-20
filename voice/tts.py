"""
Text-to-speech using ElevenLabs with streaming support.
"""

import io
import requests
from typing import Optional, Generator

from config import config


class TextToSpeech:
    """ElevenLabs TTS integration with streaming."""

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
        Convert text to speech (non-streaming, full audio).

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
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.90,
                        "similarity_boost": 0.80,
                        "style": 0.0,
                        "use_speaker_boost": True,
                    },
                },
                timeout=30,
            )
            response.raise_for_status()

            print(f"[TTS] Synthesized {len(response.content)} bytes of audio")
            return response.content

        except Exception as e:
            print(f"[TTS] Error synthesizing speech: {e}")
            return None

    def synthesize_stream(self, text: str) -> Generator[bytes, None, None]:
        """
        Convert text to speech with streaming.
        Yields audio chunks as they're generated.

        Args:
            text: The text to speak.

        Yields:
            Audio chunks (MP3 data).
        """
        try:
            print(f"[TTS] Streaming: {text[:50]}...")

            response = requests.post(
                f"{self.BASE_URL}/text-to-speech/{self.voice_id}/stream",
                headers={
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": self.api_key,
                },
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.90,
                        "similarity_boost": 0.80,
                        "style": 0.0,
                        "use_speaker_boost": True,
                    },
                },
                stream=True,
                timeout=30,
            )
            response.raise_for_status()

            chunk_count = 0
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    chunk_count += 1
                    yield chunk

            print(f"[TTS] Streamed {chunk_count} chunks")

        except Exception as e:
            print(f"[TTS] Error streaming speech: {e}")
