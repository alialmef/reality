"""
Voice listener for Alfred.
Handles microphone input, wake word detection, and speech-to-text.
"""

import io
import json
import os
import queue
import tempfile
import threading
import time
from typing import Callable, Optional, Any

import numpy as np
import sounddevice as sd
from openai import OpenAI
from scipy.io import wavfile

from config import config


def _load_audio_config():
    """Load audio configuration from config/audio.json."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "audio.json")
    try:
        with open(config_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[Listener] Warning: {config_path} not found, using default device")
        return {"microphone": {"device_index": None}}


class VoiceListener:
    """
    Listens for the wake word "Alfred" and transcribes speech.
    Uses configured microphone for voice input.
    """

    def __init__(self, input_device: int = None):
        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")

        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_duration = 0.5  # seconds per chunk
        self.silence_threshold = 0.005  # RMS threshold for silence (lower = less sensitive)
        self.silence_duration = 2.5  # seconds of silence to stop recording (longer = more patient)
        self.max_recording_duration = 90  # max seconds to record

        # Load device from config if not specified
        if input_device is None:
            audio_config = _load_audio_config()
            input_device = audio_config.get("microphone", {}).get("device_index")
        self.input_device = input_device

        self.audio_queue = queue.Queue()
        self.is_listening = False
        self.is_recording = False
        self._stop_event = threading.Event()
        self._partial_command = None  # Text said after wake word in same chunk
        self._on_wake_word = None  # Callback when wake word detected (for audio ducking)

        print(f"[Listener] Initialized (input device: {self.input_device})")

    def set_wake_word_callback(self, callback: Callable[[], None]):
        """Set a callback to be called when wake word is detected (before recording command)."""
        self._on_wake_word = callback

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for sounddevice stream."""
        if status:
            print(f"[Listener] Audio status: {status}")
        self.audio_queue.put(indata.copy())

    def _get_rms(self, audio: np.ndarray) -> float:
        """Calculate RMS (volume) of audio."""
        return np.sqrt(np.mean(audio ** 2))

    def _transcribe(self, audio: np.ndarray) -> str:
        """Send audio to Whisper API for transcription."""
        try:
            # Convert to WAV format in memory
            audio_int16 = (audio * 32767).astype(np.int16)

            # Write to temporary file (Whisper API needs a file)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wavfile.write(f.name, self.sample_rate, audio_int16)
                f.flush()

                # Send to Whisper
                with open(f.name, "rb") as audio_file:
                    response = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="en",
                    )

            return response.text.strip()

        except Exception as e:
            print(f"[Listener] Transcription error: {e}")
            return ""

    def _record_until_silence(self) -> np.ndarray:
        """Record audio until silence is detected."""
        print("[Listener] Recording...")

        chunks = []
        silence_start = None
        recording_start = time.time()

        while not self._stop_event.is_set():
            try:
                chunk = self.audio_queue.get(timeout=0.1)
                chunks.append(chunk)

                rms = self._get_rms(chunk)

                if rms < self.silence_threshold:
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start > self.silence_duration:
                        print("[Listener] Silence detected, stopping")
                        break
                else:
                    silence_start = None

                if time.time() - recording_start > self.max_recording_duration:
                    print("[Listener] Max duration reached")
                    break

            except queue.Empty:
                continue

        if chunks:
            return np.concatenate(chunks).flatten()
        return np.array([])

    def _listen_for_wake_word(self) -> bool:
        """Listen for the wake word 'Alfred'."""
        chunks = []
        chunk_count = 0
        max_chunks = int(3 / self.chunk_duration)  # 3 seconds of audio

        while not self._stop_event.is_set():
            try:
                chunk = self.audio_queue.get(timeout=0.1)
                rms = self._get_rms(chunk)

                # Only process if there's sound
                if rms > self.silence_threshold:
                    chunks.append(chunk)
                    chunk_count += 1

                    # Every ~2 seconds, check for wake word
                    if chunk_count >= max_chunks:
                        audio = np.concatenate(chunks).flatten()
                        text = self._transcribe(audio)

                        if text:
                            print(f"[Listener] Heard: {text}")

                            # Check for wake word
                            if "alfred" in text.lower():
                                # Only keep text AFTER the wake word (ignore ambient speech before it)
                                lower_text = text.lower()
                                alfred_pos = lower_text.rfind("alfred")  # Use last occurrence
                                remaining = text[alfred_pos + len("alfred"):].strip()
                                remaining = remaining.strip(",.!? ")

                                if remaining:
                                    # Store partial command to prepend later
                                    self._partial_command = remaining
                                    print(f"[Listener] Wake word detected with partial: {remaining}")

                                # Call wake word callback (e.g., to duck music)
                                if self._on_wake_word:
                                    self._on_wake_word()
                                return True

                        chunks = []
                        chunk_count = 0
                else:
                    # Reset on silence
                    if chunks:
                        # Process what we have
                        audio = np.concatenate(chunks).flatten()
                        if len(audio) > self.sample_rate * 0.5:  # At least 0.5s
                            text = self._transcribe(audio)
                            if text:
                                print(f"[Listener] Heard: {text}")
                                if "alfred" in text.lower():
                                    # Only keep text AFTER the wake word
                                    lower_text = text.lower()
                                    alfred_pos = lower_text.rfind("alfred")
                                    remaining = text[alfred_pos + len("alfred"):].strip()
                                    remaining = remaining.strip(",.!? ")
                                    if remaining:
                                        self._partial_command = remaining
                                        print(f"[Listener] Wake word detected with partial: {remaining}")
                                    # Call wake word callback (e.g., to duck music)
                                    if self._on_wake_word:
                                        self._on_wake_word()
                                    return True
                    chunks = []
                    chunk_count = 0

            except queue.Empty:
                continue

        return False

    def listen_once(self) -> Optional[str]:
        """
        Listen for wake word, then record and transcribe command.
        Returns the transcribed command, or None if stopped.
        """
        print("[Listener] Listening for 'Alfred'...")

        # Clear partial command from previous run
        self._partial_command = None

        # Clear the queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

        # Start audio stream from Yealink
        with sd.InputStream(
            device=self.input_device,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=np.float32,
            callback=self._audio_callback,
            blocksize=int(self.sample_rate * self.chunk_duration),
        ):
            # Listen for wake word
            wake_result = self._listen_for_wake_word()

            if self._stop_event.is_set():
                return None

            if wake_result:
                # Always record the full command after wake word
                print("[Listener] Wake word detected! Listening for command...")
                audio = self._record_until_silence()

                if len(audio) > 0:
                    text = self._transcribe(audio)
                    # Prepend any partial command from the wake word chunk
                    if self._partial_command and text:
                        full_command = f"{self._partial_command} {text}"
                        print(f"[Listener] Command (combined): {full_command}")
                        return full_command
                    elif text:
                        print(f"[Listener] Command: {text}")
                        return text
                    elif self._partial_command:
                        # Only had partial, no additional speech
                        print(f"[Listener] Command (partial only): {self._partial_command}")
                        return self._partial_command

        return None

    def listen_for_response(self, timeout: float = 4.0) -> Optional[str]:
        """
        Listen briefly for a response (no wake word needed).
        Used after Alfred speaks to see if user responds.

        Args:
            timeout: Max seconds to wait for speech

        Returns:
            Transcribed response, or None if silence
        """
        print(f"[Listener] Listening for response ({timeout}s)...")

        chunks = []
        speech_detected = False
        silence_start = None
        listen_start = time.time()

        # Clear the queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

        with sd.InputStream(
            device=self.input_device,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=np.float32,
            callback=self._audio_callback,
            blocksize=int(self.sample_rate * self.chunk_duration),
        ):
            while time.time() - listen_start < timeout:
                try:
                    chunk = self.audio_queue.get(timeout=0.1)
                    rms = self._get_rms(chunk)

                    if rms > self.silence_threshold:
                        chunks.append(chunk)
                        speech_detected = True
                        silence_start = None
                    elif speech_detected:
                        # We had speech, now silence - check if they're done
                        chunks.append(chunk)  # Include trailing silence
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > 1.5:  # 1.5s silence = done
                            print("[Listener] Response complete")
                            break

                except queue.Empty:
                    continue

        if not speech_detected or not chunks:
            print("[Listener] No response detected")
            return None

        # Transcribe what we got
        audio = np.concatenate(chunks).flatten()
        if len(audio) > self.sample_rate * 0.3:  # At least 0.3s of audio
            text = self._transcribe(audio)
            if text:
                print(f"[Listener] Response: {text}")
                return text

        return None

    def start_continuous(self, on_command: Callable[[str], None]):
        """
        Start continuous listening in a background thread.
        Calls on_command(text) when a command is received.
        """
        self._stop_event.clear()
        self.is_listening = True

        def listen_loop():
            while not self._stop_event.is_set():
                try:
                    command = self.listen_once()
                    if command:
                        on_command(command)
                except Exception as e:
                    print(f"[Listener] Error: {e}")
                    time.sleep(1)

        self._thread = threading.Thread(target=listen_loop, daemon=True)
        self._thread.start()
        print("[Listener] Started continuous listening")

    def stop(self):
        """Stop listening."""
        self._stop_event.set()
        self.is_listening = False
        print("[Listener] Stopped")
