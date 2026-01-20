#!/usr/bin/env python3
"""
Reality - A living home system.

The platform that powers intelligent agents in your home.
Currently running: Alfred (door greeter + voice assistant)
"""

import signal
import sys
import time

from sensors import DoorSensor
from context import ContextGatherer
from personality import GreetingGenerator
from voice import TextToSpeech, Speaker, VoiceListener
from agents.alfred import AlfredAgent
from config import config


class Reality:
    """The Reality home system."""

    def __init__(self):
        print("\n" + "=" * 50)
        print("  REALITY")
        print("  A living home system")
        print("=" * 50 + "\n")

        # Initialize components
        print("[Reality] Initializing system...")

        # Core components
        self.tts = TextToSpeech()
        self.speaker = Speaker()

        # Door sensor components
        self.door_sensor = DoorSensor()
        self.context_gatherer = ContextGatherer()
        self.greeting_generator = GreetingGenerator()

        # Voice conversation components (optional - needs OpenAI key)
        self.voice_enabled = False
        self.listener = None
        self.alfred_agent = None

        if config.OPENAI_API_KEY:
            try:
                self.listener = VoiceListener()
                # Give Alfred access to home context (door events, etc.)
                self.alfred_agent = AlfredAgent(
                    home_context_provider=self.context_gatherer.presence.get_home_context
                )
                self.voice_enabled = True
                print("[Reality] Voice conversation enabled")
            except Exception as e:
                print(f"[Reality] Voice disabled: {e}")
        else:
            print("[Reality] Voice disabled (no OPENAI_API_KEY)")

        print("[Reality] System initialized")
        print("[Reality] Agents loaded:")
        print("  - Alfred (door greeter)")
        if self.voice_enabled:
            print("  - Alfred (voice assistant) - say 'Alfred' to talk")
        print()

    def on_door_opened(self, event: dict):
        """Handle door opened event."""
        print("\n" + "-" * 40)
        print("[Reality] Door opened")

        # Gather context
        context = self.context_gatherer.gather()

        # Log timing info
        time_desc = context.get('time_since_last_description', 'unknown')
        print(f"[Reality] {context['time_of_day']}, {context['day_name']} - last door event: {time_desc}")

        # Let Alfred decide whether to greet
        print("[Reality] Asking Alfred...")
        greeting = self.greeting_generator.generate(context)
        if not greeting:
            print("[Alfred] *silence*")
            print("-" * 40 + "\n")
            return

        # Speak it
        audio = self.tts.synthesize(greeting)
        if not audio:
            print("[Reality] Failed to synthesize speech")
            return

        self.speaker.play(audio)

        # Listen for response - greeting can start a conversation
        if self.voice_enabled and self.listener:
            self._listen_after_greeting(greeting)

        print("-" * 40 + "\n")

    def _listen_after_greeting(self, greeting: str):
        """Listen briefly after greeting to see if user wants to chat."""
        response = self.listener.listen_for_response(timeout=4.0)

        if not response:
            return  # Silence - they're busy, let it go

        # They responded - start a conversation
        print(f"[Reality] User responded: {response}")

        # Prime Alfred with the greeting context so he knows what he said
        self.alfred_agent.conversation_history.append({
            "role": "assistant",
            "content": greeting
        })

        # Now handle their response as a conversation
        self._continue_conversation(response)

    def _continue_conversation(self, user_input: str):
        """Continue a conversation after initial exchange."""
        response = self.alfred_agent.respond(user_input)
        if not response:
            return

        # Speak Alfred's response
        audio_stream = self.tts.synthesize_stream(response)
        self.speaker.play_stream(audio_stream)

        # Listen for follow-up
        follow_up = self.listener.listen_for_response(timeout=5.0)
        if follow_up:
            self._continue_conversation(follow_up)

    def on_voice_command(self, command: str):
        """Handle voice command from listener."""
        print("\n" + "-" * 40)
        print(f"[Reality] Voice command: {command}")

        # Get response from Alfred
        response = self.alfred_agent.respond(command)
        if not response:
            print("[Alfred] No response")
            print("-" * 40 + "\n")
            return

        # Stream TTS
        audio_stream = self.tts.synthesize_stream(response)
        self.speaker.play_stream(audio_stream)
        print("-" * 40 + "\n")

    def run(self):
        """Start Reality and listen for events."""
        # Start door sensor
        print("[Reality] Starting door sensor...")
        self.door_sensor.start(self.on_door_opened)

        # Start voice listener if enabled
        if self.voice_enabled:
            print("[Reality] Starting voice listener...")
            self.listener.start_continuous(self.on_voice_command)

        print("[Reality] Listening. Press Ctrl+C to stop.\n")

        # Handle graceful shutdown
        def shutdown(sig, frame):
            print("\n[Reality] Shutting down...")
            self.door_sensor.stop()
            if self.listener:
                self.listener.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)

        # Keep running
        while True:
            time.sleep(1)


def main():
    """Entry point."""
    try:
        reality = Reality()
        reality.run()
    except ValueError as e:
        print(f"\n[Error] Configuration error: {e}")
        print("Please check your .env file and ensure all required API keys are set.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[Error] Failed to start Reality: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
