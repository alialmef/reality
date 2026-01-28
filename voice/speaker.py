"""
Audio playback with streaming support.
Uses progressive file playback - writes to file while mpv plays it.
Routes Alfred's voice to configured audio device.
"""

import json
import subprocess
import tempfile
import os
import threading
import time
from typing import Generator


def _load_audio_config():
    """Load audio configuration from config/audio.json."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "audio.json")
    try:
        with open(config_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[Speaker] Warning: {config_path} not found, using default device")
        return {"speaker": {"device": None}}


class Speaker:
    """Plays audio using progressive file playback."""

    def __init__(self, device: str = None):
        if device is None:
            audio_config = _load_audio_config()
            device = audio_config.get("speaker", {}).get("device")
        self.device = device
        self._mpv_process = None
        self._temp_file = None
        print(f"[Speaker] Initialized (device: {self.device})")

    def _build_mpv_cmd(self, file_path: str) -> list:
        """Build mpv command with optional device specification."""
        cmd = ["mpv", "--no-video", "--no-terminal"]
        if self.device:
            cmd.append(f"--audio-device={self.device}")
        cmd.append(file_path)
        return cmd

    def play(self, audio_bytes: bytes) -> bool:
        """Play audio bytes."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name

            try:
                subprocess.run(
                    self._build_mpv_cmd(temp_path),
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                print("[Speaker] Playback complete")
                return True
            finally:
                os.unlink(temp_path)

        except Exception as e:
            print(f"[Speaker] Error playing audio: {e}")
            return False

    def play_stream(self, audio_chunks: Generator[bytes, None, None]) -> bool:
        """
        Play streaming audio using progressive file playback.
        Writes chunks to a file while mpv plays it - best of both worlds.
        """
        try:
            # Create temp file for progressive playback
            self._temp_file = tempfile.NamedTemporaryFile(
                suffix=".mp3",
                delete=False,
                buffering=0  # Unbuffered writes
            )
            temp_path = self._temp_file.name

            # Buffer initial chunks before starting playback
            initial_bytes = 0
            initial_target = 40000  # ~0.7s of audio

            for chunk in audio_chunks:
                self._temp_file.write(chunk)
                initial_bytes += len(chunk)
                if initial_bytes >= initial_target:
                    break

            self._temp_file.flush()

            # Start mpv playing the file (it will read as we write more)
            self._mpv_process = subprocess.Popen(
                self._build_mpv_cmd(temp_path),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Continue writing remaining chunks while mpv plays
            for chunk in audio_chunks:
                self._temp_file.write(chunk)
                self._temp_file.flush()

            # Close file to signal EOF
            self._temp_file.close()
            self._temp_file = None

            # Wait for mpv to finish
            self._mpv_process.wait()

            print("[Speaker] Stream playback complete")
            return True

        except Exception as e:
            print(f"[Speaker] Error streaming audio: {e}")
            return False

        finally:
            # Cleanup
            if self._temp_file:
                self._temp_file.close()
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
            self._mpv_process = None
            self._temp_file = None

    def stop(self):
        """Stop any current playback."""
        if self._mpv_process:
            self._mpv_process.terminate()
            self._mpv_process = None
