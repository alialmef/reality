"""
User profile - learns about the resident from conversations.
Starts empty and builds understanding over time.
Implements forgetting curve and reinforcement for natural memory.
"""

import json
import uuid
import anthropic
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

from config import config


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

    def _check_contradictions(self, new_fact: str) -> List[Dict]:
        """
        Use Claude to check if a new fact contradicts existing facts.
        Returns list of contradicting facts.
        """
        active_facts = self.get_facts(min_confidence=FADE_THRESHOLD)
        if not active_facts:
            return []

        # Build list of existing facts for comparison
        existing_facts_str = "\n".join(
            f"- {f['fact']}" for f in active_facts[:10]  # Limit to top 10
        )

        try:
            client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            response = client.messages.create(
                model="claude-3-5-haiku-20241022",  # Fast and cheap
                max_tokens=200,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": f"""Does this new fact contradict any of the existing facts?

New fact: "{new_fact}"

Existing facts:
{existing_facts_str}

If there's a contradiction, respond with ONLY the contradicting fact text (exactly as written above).
If no contradiction, respond with "NONE".
Only identify clear, direct contradictions - not just differences or updates."""
                }]
            )

            result = response.content[0].text.strip()
            if result == "NONE":
                return []

            # Find the matching fact
            contradictions = []
            for fact in active_facts:
                if fact["fact"] in result or result in fact["fact"]:
                    contradictions.append(fact)

            return contradictions

        except Exception as e:
            print(f"[UserProfile] Contradiction check error: {e}")
            return []

    @property
    def name(self) -> str:
        """How Alfred addresses the user."""
        return self._data.get("name", "sir")

    def add_fact(self, fact: str, confidence: float = 0.7, source: str = "conversation"):
        """
        Add a learned fact about the user, or reinforce if already known.
        Checks for contradictions with existing facts.

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

        # Check for contradictions
        contradictions = self._check_contradictions(fact)
        contradiction_ids = []

        if contradictions:
            for c in contradictions:
                print(f"[UserProfile] Contradiction detected: '{fact}' vs '{c['fact']}'")
                contradiction_ids.append(c.get("id", "unknown"))

                # Mark both facts as having contradictions
                if "contradicts" not in c:
                    c["contradicts"] = []

        # New fact
        new_fact_id = f"fact_{uuid.uuid4().hex[:8]}"
        self._data["learned_facts"].append({
            "id": new_fact_id,
            "fact": fact,
            "confidence": min(confidence, MAX_CONFIDENCE),
            "source": source,
            "learned": datetime.now().isoformat(),
            "last_reinforced": datetime.now().isoformat(),
            "reinforcement_count": 0,
            "status": "active",
            "contradicts": contradiction_ids,
        })

        # Update contradicting facts to reference this new one
        for c in contradictions:
            if "contradicts" not in c:
                c["contradicts"] = []
            c["contradicts"].append(new_fact_id)

        self._save()

        if contradictions:
            print(f"[UserProfile] Learned (with contradictions): {fact}")
        else:
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

    def resolve_contradiction(self, keep_fact_id: str, remove_fact_id: str):
        """
        Resolve a contradiction by keeping one fact and removing another.
        Called when user clarifies which fact is correct.
        """
        keep_fact = None
        remove_fact = None

        for fact in self._data["learned_facts"]:
            if fact.get("id") == keep_fact_id:
                keep_fact = fact
            elif fact.get("id") == remove_fact_id:
                remove_fact = fact

        if keep_fact and remove_fact:
            # Remove the incorrect fact
            self._data["learned_facts"] = [
                f for f in self._data["learned_facts"]
                if f.get("id") != remove_fact_id
            ]

            # Clear contradiction reference from kept fact
            if "contradicts" in keep_fact:
                keep_fact["contradicts"] = [
                    cid for cid in keep_fact["contradicts"]
                    if cid != remove_fact_id
                ]

            # Boost confidence of kept fact (user confirmed it)
            keep_fact["confidence"] = min(keep_fact["confidence"] + 0.2, MAX_CONFIDENCE)
            keep_fact["last_reinforced"] = datetime.now().isoformat()

            self._save()
            print(f"[UserProfile] Resolved: kept '{keep_fact['fact']}', removed '{remove_fact['fact']}'")

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
            # Separate clean facts from conflicted ones
            clean_facts = [f for f in facts if not f.get("contradicts")]
            conflicted_facts = [f for f in facts if f.get("contradicts")]

            if clean_facts:
                fact_strs = [f["fact"] for f in clean_facts[:5]]
                lines.append(f"What you know: {'; '.join(fact_strs)}")

            if conflicted_facts:
                conflict_strs = [f["fact"] for f in conflicted_facts[:3]]
                lines.append(f"Uncertain (conflicting info): {'; '.join(conflict_strs)}")

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
