"""
Greeting generator.
Calls Claude to generate Alfred's greeting.
"""

import anthropic
from typing import Optional

from config import config
from personality.alfred import ALFRED_SYSTEM_PROMPT, get_greeting_prompt


class GreetingGenerator:
    """Generates greetings using Claude."""

    def __init__(self):
        if not config.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def generate(self, context: dict) -> Optional[str]:
        """
        Generate a greeting for the given context.

        Args:
            context: Dict from ContextGatherer.gather()

        Returns:
            The greeting string, or None on error.
        """
        try:
            user_message = get_greeting_prompt(context)

            print(f"[Alfred] Thinking...")

            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                temperature=1.0,  # Add variety
                system=ALFRED_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )

            full_response = response.content[0].text.strip()

            # Parse structured response
            thinking = ""
            decision = ""
            greeting = ""

            for line in full_response.split("\n"):
                line = line.strip()
                if line.upper().startswith("THINKING:"):
                    thinking = line[9:].strip()
                elif line.upper().startswith("DECISION:"):
                    decision = line[9:].strip().lower()
                elif line.upper().startswith("RESPONSE:"):
                    greeting = line[9:].strip()
                elif line.upper().startswith("GREETING:"):
                    # Fallback in case Claude uses GREETING instead
                    greeting = line[9:].strip()

            # Display Alfred's reasoning
            print(f"[Alfred] Reasoning: {thinking}")
            print(f"[Alfred] Decision: {decision}")

            # Remove any quotes if Claude wrapped it
            if greeting.startswith('"') and greeting.endswith('"'):
                greeting = greeting[1:-1]

            # Check if Alfred decided to stay silent
            if decision == "silence" or "[silence]" in greeting.lower():
                return None

            print(f"[Alfred] Says: \"{greeting}\"")
            return greeting

        except Exception as e:
            print(f"[Alfred] Error: {e}")
            return None
