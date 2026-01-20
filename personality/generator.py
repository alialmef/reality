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

            print(f"[Generator] Requesting greeting from Claude...")

            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=100,
                temperature=1.0,  # Add variety
                system=ALFRED_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )

            greeting = response.content[0].text.strip()

            # Remove any quotes if Claude wrapped it
            if greeting.startswith('"') and greeting.endswith('"'):
                greeting = greeting[1:-1]

            print(f"[Generator] Generated: {greeting}")
            return greeting

        except Exception as e:
            print(f"[Generator] Error generating greeting: {e}")
            return None
