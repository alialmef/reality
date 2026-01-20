"""
Presence tracking.
Tracks when you leave and arrive to know how long you've been gone.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class PresenceTracker:
    """
    Tracks arrivals and departures.
    Persists state to disk so it survives restarts.
    """

    def __init__(self, state_file: str = "presence_state.json"):
        self.state_file = Path(__file__).parent.parent / "data" / state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_state()

    def _load_state(self):
        """Load state from disk."""
        if self.state_file.exists():
            with open(self.state_file, "r") as f:
                data = json.load(f)
                self.last_departure = (
                    datetime.fromisoformat(data["last_departure"])
                    if data.get("last_departure")
                    else None
                )
                self.last_arrival = (
                    datetime.fromisoformat(data["last_arrival"])
                    if data.get("last_arrival")
                    else None
                )
                self.is_home = data.get("is_home", False)
        else:
            self.last_departure = None
            self.last_arrival = None
            self.is_home = False

    def _save_state(self):
        """Persist state to disk."""
        data = {
            "last_departure": (
                self.last_departure.isoformat() if self.last_departure else None
            ),
            "last_arrival": (
                self.last_arrival.isoformat() if self.last_arrival else None
            ),
            "is_home": self.is_home,
        }
        with open(self.state_file, "w") as f:
            json.dump(data, f, indent=2)

    def record_arrival(self) -> dict:
        """
        Record an arrival.
        Returns context about the arrival.
        """
        now = datetime.now()

        # Calculate time away
        seconds_away = None
        if self.last_departure:
            seconds_away = (now - self.last_departure).total_seconds()

        self.last_arrival = now
        self.is_home = True
        self._save_state()

        return {
            "arrival_time": now,
            "seconds_away": seconds_away,
            "was_already_home": self.is_home and self.last_arrival is not None,
        }

    def record_departure(self):
        """Record a departure."""
        self.last_departure = datetime.now()
        self.is_home = False
        self._save_state()

    def get_absence_description(self, seconds: Optional[float]) -> str:
        """Convert seconds away into natural language."""
        if seconds is None:
            return "unknown duration"

        minutes = seconds / 60
        hours = minutes / 60

        if minutes < 5:
            return "just a moment"
        elif minutes < 30:
            return f"about {int(minutes)} minutes"
        elif minutes < 60:
            return "about half an hour"
        elif hours < 2:
            return "about an hour"
        elif hours < 5:
            return f"about {int(hours)} hours"
        elif hours < 10:
            return "most of the day"
        else:
            return "a long time"
