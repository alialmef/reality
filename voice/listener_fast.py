"""
Fast voice listener using local wake word detection.
Uses openwakeword for instant wake word, Whisper only for command transcription.
"""

import queue
import tempfile
import threading
import time
from typing import Callable, Optional

import numpy as np
import sounddevice as sd
from openwakeword.model import Model
from openai import OpenAI
from scipy.io import wavfile

from config import config


class FastVoiceListener:
    """
    Fast listener using local wake word detection.
    Wake word: "Hey Jarvis" (local, instant)
    Command transcription: Whisper API (only after wake word)
    """

    def __init__(self):
        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")

        self.client = OpenAI(api_key=config.OPENAI_API_KEY)

        # Audio settings
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 1280  # ~80ms chunks for openwakeword

        # Recording settings
        self.silence_threshold = 0.005
        self.silence_duration = 2.0  # seconds of silence to stop recording
        self.max_recording_duration = 30

        # Wake word model (ONNX for Mac compatibility)
        self.wake_model = Model(
            wakeword_models=["hey_jarvis"],
            inference_framework="onnx"
        )
        self.wake_threshold = 0.5  # Confidence threshold

        self.audio_queue = queue.Queue()
        self.is_listening = False
        self._stop_event = threading.Event()

        print("[Listener] Initialized (local wake word: 'Hey Jarvis')")

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
            audio_int16 = (audio * 32767).astype(np.int16)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wavfile.write(f.name, self.sample_rate, audio_int16)
                f.flush()

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
        """Listen for wake word using local model (instant)."""
        while not self._stop_event.is_set():
            try:
                chunk = self.audio_queue.get(timeout=0.1)

                # Convert to int16 for openwakeword
                audio_int16 = (chunk.flatten() * 32767).astype(np.int16)

                # Run wake word detection
                prediction = self.wake_model.predict(audio_int16)

                # Check if wake word detected
                for model_name, score in prediction.items():
                    if score > self.wake_threshold:
                        print(f"[Listener] Wake word detected! (confidence: {score:.2f})")
                        return True

            except queue.Empty:
                continue

        return False

    def listen_once(self) -> Optional[str]:
        """
        Listen for wake word, then record and transcribe command.
        Returns the transcribed command, or None if stopped.
        """
        print("[Listener] Listening for 'Hey Jarvis'...")

        # Clear the queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

        # Start audio stream
        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=np.float32,
            callback=self._audio_callback,
            blocksize=self.chunk_size,
        ):
            # Listen for wake word (local, fast)
            if not self._listen_for_wake_word():
                return None

            if self._stop_event.is_set():
                return None

            # Record command (then send to Whisper)
            print("[Listener] Listening for command...")
            audio = self._record_until_silence()

            if len(audio) > 0:
                text = self._transcribe(audio)
                if text:
                    print(f"[Listener] Command: {text}")
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
