#!/usr/bin/env python3
"""
Alfred - A warm presence at your door.

Listens for the front door to open, then greets you home
with the warmth and wit of a trusted companion.
"""

import signal
import sys
import time

from sensors import DoorSensor
from context import ContextGatherer
from personality import GreetingGenerator
from voice import TextToSpeech, Speaker
from config import config


class Alfred:
    """The main Alfred orchestrator."""

    def __init__(self):
        print("\n" + "=" * 50)
        print("  ALFRED")
        print("  A warm presence at your door")
        print("=" * 50 + "\n")

        # Initialize components
        print("[Alfred] Initializing components...")

        self.door_sensor = DoorSensor()
        self.context_gatherer = ContextGatherer()
        self.greeting_generator = GreetingGenerator()
        self.tts = TextToSpeech()
        self.speaker = Speaker()

        print("[Alfred] All components initialized\n")

    def on_door_opened(self, event: dict):
        """Handle door opened event."""
        print("\n" + "-" * 40)
        print("[Alfred] Door opened!")

        # Gather context
        context = self.context_gatherer.gather()

        # Check if leaving
        if context.get("is_leaving"):
            print("[Alfred] Detected departure, not arrival. Safe travels.")
            print("-" * 40 + "\n")
            return

        print(f"[Alfred] Arrival detected: {context['time_of_day']}, away for {context['absence_description']}")

        # Check if we should greet
        if not context["should_greet"]:
            print("[Alfred] Brief absence, skipping greeting")
            return

        # Generate greeting
        greeting = self.greeting_generator.generate(context)
        if not greeting:
            print("[Alfred] Failed to generate greeting")
            return

        # Speak it
        audio = self.tts.synthesize(greeting)
        if not audio:
            print("[Alfred] Failed to synthesize speech")
            return

        self.speaker.play(audio)
        print("-" * 40 + "\n")

    def run(self):
        """Start Alfred and listen for events."""
        print("[Alfred] Starting door sensor...")
        self.door_sensor.start(self.on_door_opened)

        print("[Alfred] Listening for arrivals. Press Ctrl+C to stop.\n")

        # Handle graceful shutdown
        def shutdown(sig, frame):
            print("\n[Alfred] Shutting down...")
            self.door_sensor.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)

        # Keep running
        while True:
            time.sleep(1)


def main():
    """Entry point."""
    try:
        alfred = Alfred()
        alfred.run()
    except ValueError as e:
        print(f"\n[Error] Configuration error: {e}")
        print("Please check your .env file and ensure all required API keys are set.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[Error] Failed to start Alfred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
