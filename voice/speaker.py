"""
Audio playback with streaming support.
Plays audio through the system default output.
"""

import io
import subprocess
import tempfile
import os
import threading
from typing import Optional, Generator

import pygame


class Speaker:
    """Plays audio through system speakers with streaming support."""

    def __init__(self):
        pygame.mixer.init()
        self._mpv_process = None
        print("[Speaker] Initialized audio output")

    def play(self, audio_bytes: bytes) -> bool:
        """
        Play audio bytes (non-streaming).

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

    def play_stream(self, audio_chunks: Generator[bytes, None, None]) -> bool:
        """
        Play streaming audio chunks using mpv.
        Starts playing as soon as first chunk arrives.

        Args:
            audio_chunks: Generator yielding MP3 audio chunks.

        Returns:
            True if playback succeeded, False otherwise.
        """
        try:
            # Start mpv reading from stdin
            self._mpv_process = subprocess.Popen(
                [
                    "mpv",
                    "--no-video",
                    "--no-terminal",
                    "--",
                    "-"  # Read from stdin
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Feed chunks to mpv as they arrive
            for chunk in audio_chunks:
                if self._mpv_process.stdin:
                    self._mpv_process.stdin.write(chunk)
                    self._mpv_process.stdin.flush()

            # Close stdin to signal end of stream
            if self._mpv_process.stdin:
                self._mpv_process.stdin.close()

            # Wait for playback to finish
            self._mpv_process.wait()

            print("[Speaker] Stream playback complete")
            return True

        except FileNotFoundError:
            print("[Speaker] mpv not found, falling back to buffered playback")
            # Fallback: buffer all chunks and play with pygame
            all_audio = b"".join(audio_chunks)
            return self.play(all_audio)

        except Exception as e:
            print(f"[Speaker] Error streaming audio: {e}")
            return False

        finally:
            self._mpv_process = None

    def stop(self):
        """Stop any current playback."""
        pygame.mixer.music.stop()
        if self._mpv_process:
            self._mpv_process.terminate()
            self._mpv_process = None
