"""
Memory consolidation - synthesizes all knowledge into higher-level understanding.
Runs periodically to build a coherent picture from facts, patterns, and conversations.
"""

import json
import anthropic
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict

from config import config
from memory.user_profile import get_user_profile
from memory.conversation_store import get_conversation_store


# How often to run consolidation
CONSOLIDATION_INTERVAL_HOURS = 24


class MemoryConsolidator:
    """
    Synthesizes facts, patterns, and conversations into coherent understanding.
    Creates a 'personality sketch' and situational awareness for Alfred.
    """

    def __init__(self, understanding_file: str = "understanding.json"):
        self.understanding_file = Path(__file__).parent.parent / "data" / understanding_file
        self.understanding_file.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        """Load existing understanding from disk."""
        if self.understanding_file.exists():
            try:
                with open(self.understanding_file, "r") as f:
                    self._data = json.load(f)
            except Exception as e:
                print(f"[Consolidation] Error loading: {e}")
                self._data = self._default_understanding()
        else:
            self._data = self._default_understanding()
            self._save()

    def _default_understanding(self) -> dict:
        """Return empty understanding structure."""
        return {
            "last_consolidated": None,
            "personality_sketch": None,
            "current_situation": None,
            "communication_notes": None,
            "themes": [],
            "open_questions": [],
        }

    def _save(self):
        """Persist understanding to disk."""
        with open(self.understanding_file, "w") as f:
            json.dump(self._data, f, indent=2)

    def needs_consolidation(self) -> bool:
        """Check if enough time has passed since last consolidation."""
        last = self._data.get("last_consolidated")
        if not last:
            return True

        try:
            last_dt = datetime.fromisoformat(last)
            hours_since = (datetime.now() - last_dt).total_seconds() / 3600
            return hours_since >= CONSOLIDATION_INTERVAL_HOURS
        except Exception:
            return True

    def _gather_context(self) -> Dict:
        """Gather all available context for consolidation."""
        context = {
            "facts": [],
            "patterns": [],
            "conversations": [],
            "preferences": {},
            "routines": {},
            "interests": [],
        }

        # Get facts from user profile
        try:
            profile = get_user_profile()
            facts = profile.get_facts(min_confidence=0.3)
            context["facts"] = [f["fact"] for f in facts[:15]]
            context["preferences"] = profile._data.get("preferences", {})
            context["routines"] = profile._data.get("routines", {})
            context["interests"] = profile._data.get("interests", [])
        except Exception as e:
            print(f"[Consolidation] Error getting profile: {e}")

        # Get patterns (lazy import to avoid circular dependency)
        try:
            from context.patterns import get_pattern_detector
            detector = get_pattern_detector()
            patterns = detector.get_patterns()
            context["patterns"] = [
                p["description"] for p in patterns
                if p.get("confidence", 0) >= 0.5
            ][:10]
        except Exception as e:
            print(f"[Consolidation] Error getting patterns: {e}")

        # Get recent conversation summaries
        try:
            store = get_conversation_store()
            convos = store._data.get("conversations", [])[-10:]  # Last 10
            context["conversations"] = [
                c.get("summary", "") for c in convos if c.get("summary")
            ]
        except Exception as e:
            print(f"[Consolidation] Error getting conversations: {e}")

        return context

    def consolidate(self) -> bool:
        """
        Run consolidation to synthesize understanding.
        Uses Claude to create a coherent picture from all data.
        Returns True if successful.
        """
        if not config.ANTHROPIC_API_KEY:
            print("[Consolidation] No API key configured")
            return False

        context = self._gather_context()

        # Check if we have enough data to consolidate
        total_items = (
            len(context["facts"]) +
            len(context["patterns"]) +
            len(context["conversations"])
        )
        if total_items < 3:
            print("[Consolidation] Not enough data to consolidate yet")
            return False

        # Build context description
        context_parts = []

        if context["facts"]:
            context_parts.append(f"Known facts about them:\n- " + "\n- ".join(context["facts"]))

        if context["patterns"]:
            context_parts.append(f"Observed patterns:\n- " + "\n- ".join(context["patterns"]))

        if context["preferences"]:
            prefs = [f"{k}: {v.get('value', v)}" for k, v in context["preferences"].items()]
            context_parts.append(f"Preferences:\n- " + "\n- ".join(prefs))

        if context["routines"]:
            routines = [f"{k}: {v.get('value', v)}" for k, v in context["routines"].items()]
            context_parts.append(f"Routines:\n- " + "\n- ".join(routines))

        if context["interests"]:
            context_parts.append(f"Interests: {', '.join(context['interests'])}")

        if context["conversations"]:
            context_parts.append(f"Recent conversations:\n- " + "\n- ".join(context["conversations"]))

        context_str = "\n\n".join(context_parts)

        try:
            client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            response = client.messages.create(
                model="claude-3-5-haiku-20241022",  # Fast and cheap for synthesis
                max_tokens=800,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": f"""You are Alfred, a butler AI who has been observing and conversing with someone.
Based on everything you know, synthesize your understanding.

{context_str}

Respond in JSON format with these fields:
{{
  "personality_sketch": "A 2-3 sentence description of who this person seems to be - their character, tendencies, what matters to them.",
  "current_situation": "A brief note on what they seem focused on currently (or null if unclear).",
  "communication_notes": "How they prefer to communicate - brief observations (or null if unknown).",
  "themes": ["List of 2-4 recurring themes or interests you've noticed"],
  "open_questions": ["List of 2-3 things you're still curious about or unsure of"]
}}

Be concise and insightful. Only include what you can reasonably infer - don't make things up."""
                }]
            )

            result_text = response.content[0].text.strip()

            # Parse JSON response
            # Handle potential markdown code blocks
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]

            understanding = json.loads(result_text)

            # Update our understanding
            self._data["personality_sketch"] = understanding.get("personality_sketch")
            self._data["current_situation"] = understanding.get("current_situation")
            self._data["communication_notes"] = understanding.get("communication_notes")
            self._data["themes"] = understanding.get("themes", [])
            self._data["open_questions"] = understanding.get("open_questions", [])
            self._data["last_consolidated"] = datetime.now().isoformat()

            self._save()
            print(f"[Consolidation] Understanding updated")
            return True

        except json.JSONDecodeError as e:
            print(f"[Consolidation] Failed to parse response: {e}")
            return False
        except Exception as e:
            print(f"[Consolidation] Error: {e}")
            return False

    def get_context(self) -> Optional[str]:
        """Format understanding as context for prompts."""
        lines = []

        if self._data.get("personality_sketch"):
            lines.append(f"Your sense of who they are: {self._data['personality_sketch']}")

        if self._data.get("current_situation"):
            lines.append(f"Current focus: {self._data['current_situation']}")

        if self._data.get("communication_notes"):
            lines.append(f"Communication style: {self._data['communication_notes']}")

        if self._data.get("themes"):
            lines.append(f"Recurring themes: {', '.join(self._data['themes'][:3])}")

        return "\n".join(lines) if lines else None

    def maybe_consolidate(self) -> bool:
        """Run consolidation if enough time has passed."""
        if self.needs_consolidation():
            return self.consolidate()
        return False


# Singleton instance
_consolidator = None


def get_consolidator() -> MemoryConsolidator:
    """Get the memory consolidator singleton."""
    global _consolidator
    if _consolidator is None:
        _consolidator = MemoryConsolidator()
    return _consolidator


def get_understanding_context() -> Optional[str]:
    """Convenience function to get understanding context."""
    return get_consolidator().get_context()
