"""
Relationship graph - tracks people mentioned in conversations.
Alfred remembers friends, family, colleagues - their names, relationship to user,
and details about them. Supports fuzzy name matching and disambiguation.
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
from difflib import SequenceMatcher


class RelationshipGraph:
    """
    Stores and retrieves information about people in the user's life.
    People are learned from conversations and can be looked up by name.
    """

    def __init__(self, store_file: str = "relationships.json"):
        self.store_file = Path(__file__).parent.parent / "data" / store_file
        self.store_file.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        """Load relationships from disk."""
        if self.store_file.exists():
            try:
                with open(self.store_file, "r") as f:
                    self._data = json.load(f)
            except Exception as e:
                print(f"[RelationshipGraph] Error loading: {e}")
                self._data = self._default_store()
        else:
            self._data = self._default_store()
            self._save()

    def _default_store(self) -> dict:
        """Return empty store structure."""
        return {
            "people": {},
            "pending_clarifications": [],
        }

    def _save(self):
        """Persist store to disk."""
        with open(self.store_file, "w") as f:
            json.dump(self._data, f, indent=2)

    def _generate_key(self, name: str, relationship_type: str = None) -> str:
        """Generate a unique key for a person."""
        base = name.lower().replace(" ", "_")
        if relationship_type:
            base = f"{base}_{relationship_type}"
        # Ensure uniqueness
        if base in self._data["people"]:
            base = f"{base}_{uuid.uuid4().hex[:4]}"
        return base

    def _name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names (0.0-1.0)."""
        return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()

    def find_by_name(self, name: str, threshold: float = 0.7) -> List[Dict]:
        """
        Find people by name using fuzzy matching.

        Args:
            name: The name to search for
            threshold: Minimum similarity score (0.0-1.0)

        Returns:
            List of matching people with their keys and scores
        """
        matches = []
        name_lower = name.lower()

        for key, person in self._data["people"].items():
            if person.get("status") == "removed":
                continue

            # Check primary name
            primary_score = self._name_similarity(name, person["name"])
            if primary_score >= threshold:
                matches.append({
                    "key": key,
                    "person": person,
                    "score": primary_score,
                    "matched_on": "name"
                })
                continue

            # Check aliases
            for alias in person.get("aliases", []):
                alias_score = self._name_similarity(name, alias)
                if alias_score >= threshold:
                    matches.append({
                        "key": key,
                        "person": person,
                        "score": alias_score,
                        "matched_on": alias
                    })
                    break

            # Check if input is partial match (e.g., "Marcus" matches "Marcus from Brooklyn")
            if name_lower in person["name"].lower():
                matches.append({
                    "key": key,
                    "person": person,
                    "score": 0.8,
                    "matched_on": "partial"
                })

        # Sort by score descending
        matches.sort(key=lambda m: m["score"], reverse=True)
        return matches

    def get_person(self, key: str) -> Optional[Dict]:
        """Get a person by their key."""
        return self._data["people"].get(key)

    def add_person(
        self,
        name: str,
        relationship_type: str = "acquaintance",
        details: List[str] = None,
        aliases: List[str] = None,
    ) -> str:
        """
        Add a new person to the graph.

        Returns:
            The key for the new person
        """
        key = self._generate_key(name, relationship_type)
        now = datetime.now().isoformat()

        self._data["people"][key] = {
            "id": f"person_{uuid.uuid4().hex[:8]}",
            "name": name,
            "aliases": aliases or [],
            "relationship_type": relationship_type,
            "details": [
                {
                    "fact": detail,
                    "confidence": 0.7,
                    "learned": now
                }
                for detail in (details or [])
            ],
            "first_mentioned": now,
            "last_mentioned": now,
            "mention_count": 1,
            "expected_visits": [],
            "status": "active",
        }

        self._save()
        print(f"[RelationshipGraph] Added: {name} ({relationship_type})")
        return key

    def update_person(self, key: str, **kwargs):
        """Update a person's attributes."""
        if key not in self._data["people"]:
            return False

        person = self._data["people"][key]

        for field in ["name", "relationship_type", "aliases", "status"]:
            if field in kwargs:
                person[field] = kwargs[field]

        self._save()
        return True

    def add_detail(self, key: str, detail: str, confidence: float = 0.7):
        """Add a detail/fact about a person."""
        if key not in self._data["people"]:
            return False

        person = self._data["people"][key]

        # Check if detail already exists
        for existing in person["details"]:
            if existing["fact"].lower() == detail.lower():
                # Reinforce existing detail
                existing["confidence"] = min(1.0, existing["confidence"] + 0.1)
                self._save()
                return True

        person["details"].append({
            "fact": detail,
            "confidence": confidence,
            "learned": datetime.now().isoformat(),
        })

        self._save()
        print(f"[RelationshipGraph] Added detail for {person['name']}: {detail}")
        return True

    def add_alias(self, key: str, alias: str):
        """Add an alias for a person."""
        if key not in self._data["people"]:
            return False

        person = self._data["people"][key]
        if alias not in person["aliases"]:
            person["aliases"].append(alias)
            self._save()
        return True

    def record_mention(self, key: str):
        """Record that a person was mentioned."""
        if key not in self._data["people"]:
            return False

        person = self._data["people"][key]
        person["mention_count"] = person.get("mention_count", 0) + 1
        person["last_mentioned"] = datetime.now().isoformat()
        self._save()
        return True

    def set_expected_visit(self, key: str, when: str, note: str = None):
        """Record that a person is expected to visit."""
        if key not in self._data["people"]:
            return False

        person = self._data["people"][key]
        person["expected_visits"].append({
            "when": when,
            "note": note,
            "added": datetime.now().isoformat(),
        })
        self._save()
        print(f"[RelationshipGraph] {person['name']} expected: {when}")
        return True

    def process_mention(
        self,
        name: str,
        relationship_type: str = None,
        details: List[str] = None,
        visiting: bool = False,
        visit_time: str = None,
    ) -> Dict:
        """
        Process a mention of a person from conversation.
        Handles disambiguation and creates/updates as needed.

        Returns:
            Dict with 'action' (created/updated/ambiguous) and 'key' or 'matches'
        """
        matches = self.find_by_name(name)

        if not matches:
            # No matches - create new person
            key = self.add_person(
                name=name,
                relationship_type=relationship_type or "acquaintance",
                details=details,
            )
            if visiting:
                self.set_expected_visit(key, visit_time or "soon")
            return {"action": "created", "key": key}

        if len(matches) == 1:
            # Exact match - update existing
            match = matches[0]
            key = match["key"]
            self.record_mention(key)

            # Update relationship type if provided and more specific
            if relationship_type and relationship_type != "acquaintance":
                self.update_person(key, relationship_type=relationship_type)

            # Add new details
            for detail in (details or []):
                self.add_detail(key, detail)

            if visiting:
                self.set_expected_visit(key, visit_time or "soon")

            return {"action": "updated", "key": key}

        # Multiple matches - try auto-resolve
        resolved = self._auto_resolve(matches, relationship_type)
        if resolved:
            key = resolved["key"]
            self.record_mention(key)

            if relationship_type and relationship_type != "acquaintance":
                self.update_person(key, relationship_type=relationship_type)

            for detail in (details or []):
                self.add_detail(key, detail)

            if visiting:
                self.set_expected_visit(key, visit_time or "soon")

            return {"action": "updated", "key": key}

        # Can't auto-resolve - queue for clarification
        self._add_pending_clarification(name, matches)
        return {"action": "ambiguous", "matches": matches}

    def _auto_resolve(self, matches: List[Dict], relationship_hint: str = None) -> Optional[Dict]:
        """
        Try to automatically resolve ambiguous matches.

        Heuristics:
        1. If relationship hint matches one person's type, use that
        2. If one person was mentioned recently (last 7 days), prefer them
        3. If one person has expected visits, prefer them
        """
        now = datetime.now()
        week_ago = (now - timedelta(days=7)).isoformat()

        # Heuristic 1: Relationship type match
        if relationship_hint:
            type_matches = [
                m for m in matches
                if m["person"].get("relationship_type") == relationship_hint
            ]
            if len(type_matches) == 1:
                return type_matches[0]

        # Heuristic 2: Recently mentioned
        recent_matches = [
            m for m in matches
            if m["person"].get("last_mentioned", "") > week_ago
        ]
        if len(recent_matches) == 1:
            return recent_matches[0]

        # Heuristic 3: Has expected visits
        visiting_matches = [
            m for m in matches
            if m["person"].get("expected_visits")
        ]
        if len(visiting_matches) == 1:
            return visiting_matches[0]

        return None

    def _add_pending_clarification(self, name: str, matches: List[Dict]):
        """Add a pending clarification for an ambiguous name."""
        # Remove old clarification for same name
        self._data["pending_clarifications"] = [
            c for c in self._data["pending_clarifications"]
            if c["name"].lower() != name.lower()
        ]

        self._data["pending_clarifications"].append({
            "name": name,
            "matches": [
                {
                    "key": m["key"],
                    "name": m["person"]["name"],
                    "relationship_type": m["person"].get("relationship_type"),
                }
                for m in matches
            ],
            "added": datetime.now().isoformat(),
        })

        self._save()
        print(f"[RelationshipGraph] Queued clarification for: {name}")

    def get_pending_clarification(self) -> Optional[Dict]:
        """Get the oldest pending clarification, if any."""
        if not self._data["pending_clarifications"]:
            return None
        return self._data["pending_clarifications"][0]

    def resolve_clarification(self, name: str, chosen_key: str):
        """Resolve a pending clarification by choosing which person was meant."""
        # Remove from pending
        self._data["pending_clarifications"] = [
            c for c in self._data["pending_clarifications"]
            if c["name"].lower() != name.lower()
        ]

        # Update the chosen person
        if chosen_key in self._data["people"]:
            self.record_mention(chosen_key)

        self._save()

    def get_context(self, max_close: int = 5, max_others: int = 5) -> Optional[str]:
        """
        Format relationships as context for prompts.
        Returns None if no people known.
        """
        if not self._data["people"]:
            return None

        # Categorize people
        close_types = {
            "family", "friend", "partner", "roommate",
            "brother", "sister", "mother", "father", "parent",
            "son", "daughter", "spouse", "wife", "husband"
        }
        close_people = []
        other_people = []

        for key, person in self._data["people"].items():
            if person.get("status") == "removed":
                continue

            rel_type = person.get("relationship_type", "acquaintance")

            entry = {
                "name": person["name"],
                "type": rel_type,
                "details": [d["fact"] for d in person.get("details", [])],  # All details
                "expected_visits": person.get("expected_visits", []),
                "mention_count": person.get("mention_count", 0),
                "last_mentioned": person.get("last_mentioned"),
            }

            if rel_type in close_types:
                close_people.append(entry)
            else:
                other_people.append(entry)

        # Sort by mention count (most mentioned first)
        close_people.sort(key=lambda p: p["mention_count"], reverse=True)
        other_people.sort(key=lambda p: p["mention_count"], reverse=True)

        lines = []

        # Close people section - with full details
        if close_people:
            lines.append("Close people:")
            for person in close_people[:max_close]:
                lines.append(f"\n{person['name']} ({person['type']}):")

                # Show all details
                if person["details"]:
                    for detail in person["details"]:
                        lines.append(f"  - {detail}")

                # Show expected visits
                visits = person.get("expected_visits", [])
                if visits:
                    latest = visits[-1]
                    lines.append(f"  - Expected: {latest.get('when', 'soon')} ({latest.get('note', '')})")

        # Others section - with full details
        if other_people:
            lines.append("\nOthers mentioned:")
            for person in other_people[:max_others]:
                lines.append(f"\n{person['name']} ({person['type']}):")

                if person["details"]:
                    for detail in person["details"]:
                        lines.append(f"  - {detail}")

                visits = person.get("expected_visits", [])
                if visits:
                    latest = visits[-1]
                    lines.append(f"  - Expected: {latest.get('when', 'soon')} ({latest.get('note', '')})")

        return "\n".join(lines) if lines else None

    def get_all_people(self) -> List[Dict]:
        """Get all active people."""
        return [
            {"key": key, **person}
            for key, person in self._data["people"].items()
            if person.get("status") != "removed"
        ]


# Singleton instance
_graph = None


def get_relationship_graph() -> RelationshipGraph:
    """Get the relationship graph singleton."""
    global _graph
    if _graph is None:
        _graph = RelationshipGraph()
    return _graph


def get_relationships_context() -> Optional[str]:
    """Convenience function to get formatted relationships."""
    return get_relationship_graph().get_context()
