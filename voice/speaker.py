"""
Audio playback.
Plays audio through the system default output.
"""

import io
import tempfile
import os
from typing import Optional

import pygame


class Speaker:
    """Plays audio through system speakers."""

    def __init__(self):
        pygame.mixer.init()
        print("[Speaker] Initialized audio output")

    def play(self, audio_bytes: bytes) -> bool:
        """
        Play audio bytes.

        Args:
            audio_bytes: MP3 audio data.

        Returns:
            True if playback succeeded, False otherwise.
        """
        try:
            # Write to temp file (pygame needs a file)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name

            try:
                pygame.mixer.music.load(temp_path)
                pygame.mixer.music.play()

                # Wait for playback to finish
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(100)

                print("[Speaker] Playback complete")
                return True

            finally:
                # Clean up temp file
                os.unlink(temp_path)

        except Exception as e:
            print(f"[Speaker] Error playing audio: {e}")
            return False

    def stop(self):
        """Stop any current playback."""
        pygame.mixer.music.stop()
