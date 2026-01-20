"""
Simple door event tracking.
Just tracks when the door was last opened - no guessing about enter/exit.
Feeds events to pattern detector for routine learning.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

from context.patterns import get_pattern_detector


# How much history to keep for pattern analysis
HISTORY_RETENTION_DAYS = 30


class PresenceTracker:
    """
    Tracks door events simply.
    No assumptions about entering vs exiting - just raw timing.
    Maintains history for pattern awareness.
    """

    def __init__(self, state_file: str = "door_state.json"):
        self.state_file = Path(__file__).parent.parent / "data" / state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_state()

    def _load_state(self):
        """Load state from disk."""
        if self.state_file.exists():
            with open(self.state_file, "r") as f:
                data = json.load(f)
                self.last_door_event = (
                    datetime.fromisoformat(data["last_door_event"])
                    if data.get("last_door_event")
                    else None
                )
                # Load event history (list of ISO timestamps)
                self.event_history = [
                    datetime.fromisoformat(ts)
                    for ts in data.get("event_history", [])
                ]
        else:
            self.last_door_event = None
            self.event_history = []

    def _save_state(self):
        """Persist state to disk."""
        # Keep history for pattern analysis
        cutoff = datetime.now() - timedelta(days=HISTORY_RETENTION_DAYS)
        self.event_history = [e for e in self.event_history if e > cutoff]

        data = {
            "last_door_event": (
                self.last_door_event.isoformat() if self.last_door_event else None
            ),
            "event_history": [e.isoformat() for e in self.event_history],
        }
        with open(self.state_file, "w") as f:
            json.dump(data, f, indent=2)

    def record_door_event(self) -> dict:
        """
        Record a door open event.
        Returns timing info for Claude to reason about.
        Triggers pattern analysis to learn routines.
        """
        now = datetime.now()

        # Calculate time since last door event
        seconds_since_last = None
        if self.last_door_event:
            seconds_since_last = (now - self.last_door_event).total_seconds()

        # Update state
        previous_event = self.last_door_event
        self.last_door_event = now
        self.event_history.append(now)
        self._save_state()

        # Analyze patterns (promotes strong patterns to user profile routines)
        self._analyze_patterns()

        return {
            "current_time": now,
            "previous_door_event": previous_event,
            "seconds_since_last": seconds_since_last,
        }

    def _analyze_patterns(self):
        """Feed events to pattern detector for routine learning."""
        if len(self.event_history) >= 5:  # Minimum needed for pattern detection
            try:
                detector = get_pattern_detector()
                detector.update_patterns(self.event_history)
            except Exception as e:
                print(f"[PresenceTracker] Pattern analysis error: {e}")

    def get_today_count(self) -> int:
        """Count door events today."""
        today = datetime.now().date()
        return sum(1 for e in self.event_history if e.date() == today)

    def get_week_summary(self) -> dict:
        """Get summary of door events over the past week."""
        now = datetime.now()
        today = now.date()

        summary = {
            "today": 0,
            "yesterday": 0,
            "this_week": 0,
        }

        for event in self.event_history:
            event_date = event.date()
            days_ago = (today - event_date).days

            if days_ago == 0:
                summary["today"] += 1
            elif days_ago == 1:
                summary["yesterday"] += 1

            if days_ago < 7:
                summary["this_week"] += 1

        return summary

    def get_home_context(self) -> str:
        """
        Get a natural language summary of home activity for Alfred.
        Includes detected patterns and routines.
        """
        now = datetime.now()
        summary = self.get_week_summary()

        lines = []

        # Last door event
        if self.last_door_event:
            time_ago = self.get_time_description(
                (now - self.last_door_event).total_seconds()
            )
            lines.append(f"Last door activity: {time_ago} ago")
        else:
            lines.append("No recent door activity recorded")

        # Today's activity
        if summary["today"] > 0:
            lines.append(f"Door events today: {summary['today']}")

        # Yesterday comparison
        if summary["yesterday"] > 0:
            lines.append(f"Door events yesterday: {summary['yesterday']}")

        # Include detected patterns
        try:
            detector = get_pattern_detector()
            pattern_context = detector.get_context()
            if pattern_context:
                lines.append("")
                lines.append(pattern_context)
        except Exception:
            pass

        return "\n".join(lines)

    def get_time_description(self, seconds: Optional[float]) -> str:
        """Convert seconds into natural language."""
        if seconds is None:
            return "unknown (first event)"

        minutes = seconds / 60
        hours = minutes / 60

        if seconds < 30:
            return f"{int(seconds)} seconds"
        elif minutes < 2:
            return f"about {int(minutes)} minute"
        elif minutes < 60:
            return f"about {int(minutes)} minutes"
        elif hours < 2:
            return f"about {hours:.1f} hours"
        elif hours < 24:
            return f"about {int(hours)} hours"
        else:
            days = hours / 24
            return f"about {days:.1f} days"
