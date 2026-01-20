"""
User profile - learns about the resident from conversations.
Starts empty and builds understanding over time.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict


class UserProfile:
    """
    Stores and retrieves information Alfred learns about the user.
    Facts are learned from conversations and stored with confidence.
    """

    def __init__(self, profile_file: str = "user_profile.json"):
        self.profile_file = Path(__file__).parent.parent / "data" / profile_file
        self.profile_file.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        """Load profile from disk."""
        if self.profile_file.exists():
            try:
                with open(self.profile_file, "r") as f:
                    self._data = json.load(f)
            except Exception as e:
                print(f"[UserProfile] Error loading: {e}")
                self._data = self._default_profile()
        else:
            self._data = self._default_profile()
            self._save()

    def _default_profile(self) -> dict:
        """Return empty profile structure."""
        return {
            "name": "sir",
            "learned_facts": [],
            "preferences": {},
            "routines": {},
            "interests": [],
            "important_dates": {},
        }

    def _save(self):
        """Persist profile to disk."""
        with open(self.profile_file, "w") as f:
            json.dump(self._data, f, indent=2)

    @property
    def name(self) -> str:
        """How Alfred addresses the user."""
        return self._data.get("name", "sir")

    def add_fact(self, fact: str, confidence: float = 0.7, source: str = "conversation"):
        """
        Add a learned fact about the user.

        Args:
            fact: The fact learned (e.g., "Works in technology")
            confidence: How confident Alfred is (0.0-1.0)
            source: Where this was learned from
        """
        # Check for duplicates
        for existing in self._data["learned_facts"]:
            if existing["fact"].lower() == fact.lower():
                # Update confidence if higher
                if confidence > existing["confidence"]:
                    existing["confidence"] = confidence
                    existing["updated"] = datetime.now().isoformat()
                self._save()
                return

        self._data["learned_facts"].append({
            "fact": fact,
            "confidence": confidence,
            "source": source,
            "learned": datetime.now().isoformat(),
        })
        self._save()
        print(f"[UserProfile] Learned: {fact}")

    def add_preference(self, key: str, value: str, source: str = "conversation"):
        """Add or update a preference."""
        self._data["preferences"][key] = {
            "value": value,
            "source": source,
            "updated": datetime.now().isoformat(),
        }
        self._save()
        print(f"[UserProfile] Preference: {key} = {value}")

    def add_interest(self, interest: str):
        """Add an interest if not already tracked."""
        if interest.lower() not in [i.lower() for i in self._data["interests"]]:
            self._data["interests"].append(interest)
            self._save()
            print(f"[UserProfile] Interest: {interest}")

    def add_routine(self, key: str, value: str, source: str = "observed"):
        """Add or update a routine pattern."""
        self._data["routines"][key] = {
            "value": value,
            "source": source,
            "updated": datetime.now().isoformat(),
        }
        self._save()

    def add_important_date(self, name: str, date: str):
        """Add an important date (birthday, anniversary, etc.)."""
        self._data["important_dates"][name] = date
        self._save()

    def get_facts(self, min_confidence: float = 0.5) -> List[Dict]:
        """Get facts above a confidence threshold."""
        return [
            f for f in self._data["learned_facts"]
            if f["confidence"] >= min_confidence
        ]

    def get_context(self) -> Optional[str]:
        """
        Format profile as context for prompts.
        Returns None if profile is essentially empty.
        """
        lines = []

        # Name
        if self._data["name"] != "sir":
            lines.append(f"Address them as: {self._data['name']}")

        # High-confidence facts
        facts = self.get_facts(min_confidence=0.6)
        if facts:
            fact_strs = [f["fact"] for f in facts[:5]]  # Top 5
            lines.append(f"What you know: {'; '.join(fact_strs)}")

        # Preferences
        if self._data["preferences"]:
            prefs = [f"{k}: {v['value']}" for k, v in list(self._data["preferences"].items())[:3]]
            lines.append(f"Preferences: {'; '.join(prefs)}")

        # Interests
        if self._data["interests"]:
            lines.append(f"Interests: {', '.join(self._data['interests'][:5])}")

        # Routines
        if self._data["routines"]:
            routines = [f"{k}: {v['value']}" for k, v in list(self._data["routines"].items())[:3]]
            lines.append(f"Routines: {'; '.join(routines)}")

        return "\n".join(lines) if lines else None


# Singleton instance
_profile = None


def get_user_profile() -> UserProfile:
    """Get the user profile singleton."""
    global _profile
    if _profile is None:
        _profile = UserProfile()
    return _profile


def get_profile_context() -> Optional[str]:
    """Convenience function to get formatted profile."""
    return get_user_profile().get_context()
