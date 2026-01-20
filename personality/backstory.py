"""
Alfred's backstory - loaded from user-customizable JSON.
"""

import json
from pathlib import Path
from typing import Optional


class Backstory:
    """Loads and formats Alfred's backstory for prompts."""

    def __init__(self, backstory_file: str = "backstory.json"):
        self.backstory_file = Path(__file__).parent.parent / "data" / backstory_file
        self._backstory = self._load()

    def _load(self) -> dict:
        """Load backstory from JSON file."""
        if self.backstory_file.exists():
            try:
                with open(self.backstory_file, "r") as f:
                    data = json.load(f)
                    # Remove the notes field if present
                    data.pop("notes", None)
                    return data
            except Exception as e:
                print(f"[Backstory] Error loading: {e}")
        return {}

    def has_backstory(self) -> bool:
        """Check if any backstory has been defined."""
        return any(
            v for k, v in self._backstory.items()
            if v and k != "notes"
        )

    def get_context(self) -> Optional[str]:
        """
        Format backstory as context for prompts.
        Returns None if no backstory defined.
        """
        if not self.has_backstory():
            return None

        lines = []

        # Core identity
        if self._backstory.get("origin"):
            lines.append(self._backstory['origin'])

        if self._backstory.get("nature"):
            lines.append(self._backstory['nature'])

        # Understanding of Reality system
        if self._backstory.get("reality_system"):
            lines.append(self._backstory['reality_system'])

        # Memory and learning
        if self._backstory.get("memory"):
            lines.append(self._backstory['memory'])

        if self._backstory.get("learning"):
            lines.append(self._backstory['learning'])

        if self._backstory.get("curiosity"):
            lines.append(self._backstory['curiosity'])

        if self._backstory.get("consolidation"):
            lines.append(self._backstory['consolidation'])

        # Self-awareness
        if self._backstory.get("self_awareness"):
            lines.append(self._backstory['self_awareness'])

        # Relationship
        if self._backstory.get("relationship"):
            lines.append(self._backstory['relationship'])

        # Values and quirks
        if self._backstory.get("values"):
            values = "; ".join(self._backstory["values"])
            lines.append(f"Your values: {values}")

        if self._backstory.get("quirks"):
            quirks = "; ".join(self._backstory["quirks"])
            lines.append(f"Your quirks: {quirks}")

        # Legacy fields for backwards compatibility
        if self._backstory.get("age"):
            lines.append(f"Age: {self._backstory['age']}")

        if self._backstory.get("history"):
            lines.append(f"History: {self._backstory['history']}")

        if self._backstory.get("personality_formation"):
            lines.append(f"Character formed by: {self._backstory['personality_formation']}")

        return "\n\n".join(lines) if lines else None


# Singleton instance
_backstory = None


def get_backstory() -> Backstory:
    """Get the backstory singleton."""
    global _backstory
    if _backstory is None:
        _backstory = Backstory()
    return _backstory


def get_backstory_context() -> Optional[str]:
    """Convenience function to get formatted backstory."""
    return get_backstory().get_context()
