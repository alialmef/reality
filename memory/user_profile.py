"""
User profile - learns about the resident from conversations.
Starts empty and builds understanding over time.
Implements forgetting curve and reinforcement for natural memory.
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict


# Memory constants
CONFIDENCE_DECAY_PER_WEEK = 0.1   # Facts lose confidence over time
REINFORCEMENT_BOOST = 0.2         # Hearing fact again boosts confidence
MAX_CONFIDENCE = 1.0
FADE_THRESHOLD = 0.3              # Below this, excluded from prompts
FORGET_THRESHOLD = 0.1            # Below this, can be pruned


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

    def _calculate_effective_confidence(self, fact: Dict) -> float:
        """
        Calculate effective confidence with decay over time.
        Facts lose CONFIDENCE_DECAY_PER_WEEK confidence each week since last reinforcement.
        """
        # Use last_reinforced if available, otherwise learned date
        reference_date = fact.get("last_reinforced") or fact.get("learned")
        if not reference_date:
            return fact.get("confidence", 0)

        try:
            ref_dt = datetime.fromisoformat(reference_date)
            days_elapsed = (datetime.now() - ref_dt).days
            weeks_elapsed = days_elapsed / 7

            base_confidence = fact.get("confidence", 0)
            decay = weeks_elapsed * CONFIDENCE_DECAY_PER_WEEK
            effective = base_confidence - decay

            return max(0, min(MAX_CONFIDENCE, effective))
        except Exception:
            return fact.get("confidence", 0)

    def _find_similar_fact(self, new_fact: str) -> Optional[Dict]:
        """Find an existing fact that matches the new one."""
        new_lower = new_fact.lower().strip()
        for existing in self._data["learned_facts"]:
            if existing["fact"].lower().strip() == new_lower:
                return existing
        return None

    @property
    def name(self) -> str:
        """How Alfred addresses the user."""
        return self._data.get("name", "sir")

    def add_fact(self, fact: str, confidence: float = 0.7, source: str = "conversation"):
        """
        Add a learned fact about the user, or reinforce if already known.

        Args:
            fact: The fact learned (e.g., "Works in technology")
            confidence: How confident Alfred is (0.0-1.0)
            source: Where this was learned from
        """
        existing = self._find_similar_fact(fact)

        if existing:
            # Reinforce existing fact
            self._reinforce_fact(existing, source)
            return

        # New fact
        self._data["learned_facts"].append({
            "id": f"fact_{uuid.uuid4().hex[:8]}",
            "fact": fact,
            "confidence": min(confidence, MAX_CONFIDENCE),
            "source": source,
            "learned": datetime.now().isoformat(),
            "last_reinforced": datetime.now().isoformat(),
            "reinforcement_count": 0,
            "status": "active",
        })
        self._save()
        print(f"[UserProfile] Learned: {fact}")

    def _reinforce_fact(self, fact: Dict, source: str = "conversation"):
        """
        Reinforce an existing fact - boosts confidence and resets decay.
        Called when we hear the same fact again.
        """
        old_confidence = fact.get("confidence", 0)
        new_confidence = min(old_confidence + REINFORCEMENT_BOOST, MAX_CONFIDENCE)

        fact["confidence"] = new_confidence
        fact["last_reinforced"] = datetime.now().isoformat()
        fact["reinforcement_count"] = fact.get("reinforcement_count", 0) + 1

        self._save()
        print(f"[UserProfile] Reinforced: {fact['fact']} ({old_confidence:.1f} → {new_confidence:.1f})")

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
        """
        Get facts above a confidence threshold.
        Uses effective confidence (with decay applied).
        """
        result = []
        for fact in self._data["learned_facts"]:
            if fact.get("status") == "forgotten":
                continue

            effective_conf = self._calculate_effective_confidence(fact)

            # Update status based on effective confidence
            if effective_conf < FORGET_THRESHOLD:
                fact["status"] = "forgotten"
            elif effective_conf < FADE_THRESHOLD:
                fact["status"] = "faded"
            else:
                fact["status"] = "active"

            if effective_conf >= min_confidence:
                result.append({
                    **fact,
                    "effective_confidence": effective_conf,
                })

        # Sort by effective confidence (highest first)
        result.sort(key=lambda f: f["effective_confidence"], reverse=True)
        return result

    def prune_forgotten(self) -> int:
        """
        Remove facts that have decayed below the forget threshold.
        Returns count of pruned facts.
        """
        before_count = len(self._data["learned_facts"])
        self._data["learned_facts"] = [
            f for f in self._data["learned_facts"]
            if self._calculate_effective_confidence(f) >= FORGET_THRESHOLD
        ]
        after_count = len(self._data["learned_facts"])
        pruned = before_count - after_count

        if pruned > 0:
            self._save()
            print(f"[UserProfile] Pruned {pruned} forgotten facts")

        return pruned

    def get_context(self) -> Optional[str]:
        """
        Format profile as context for prompts.
        Returns None if profile is essentially empty.
        """
        lines = []

        # Name
        if self._data["name"] != "sir":
            lines.append(f"Address them as: {self._data['name']}")

        # Active facts (above fade threshold)
        facts = self.get_facts(min_confidence=FADE_THRESHOLD)
        if facts:
            fact_strs = [f["fact"] for f in facts[:5]]  # Top 5 by confidence
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
