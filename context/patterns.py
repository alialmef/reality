"""
Pattern detection - analyzes door events to detect behavioral patterns.
Promotes strong patterns to routines in the user profile.
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

from memory.user_profile import get_user_profile


# Pattern detection constants
MIN_OBSERVATIONS = 5           # Need at least this many to establish pattern
CONFIDENCE_THRESHOLD = 0.6     # Confidence needed to promote to routine
TIME_BUCKET_MINUTES = 30       # Group events into 30-min buckets


class PatternDetector:
    """
    Detects recurring patterns from door events.
    Patterns that reach threshold are promoted to user profile routines.
    """

    def __init__(self, patterns_file: str = "patterns.json"):
        self.patterns_file = Path(__file__).parent.parent / "data" / patterns_file
        self.patterns_file.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        """Load patterns from disk."""
        if self.patterns_file.exists():
            try:
                with open(self.patterns_file, "r") as f:
                    self._data = json.load(f)
            except Exception as e:
                print(f"[PatternDetector] Error loading: {e}")
                self._data = self._default_data()
        else:
            self._data = self._default_data()
            self._save()

    def _default_data(self) -> dict:
        """Return empty patterns structure."""
        return {
            "door_patterns": [],
            "activity_patterns": [],
            "last_analysis": None,
        }

    def _save(self):
        """Persist patterns to disk."""
        with open(self.patterns_file, "w") as f:
            json.dump(self._data, f, indent=2)

    def _time_bucket(self, dt: datetime) -> str:
        """Convert time to 30-minute bucket string."""
        bucket_minute = (dt.minute // TIME_BUCKET_MINUTES) * TIME_BUCKET_MINUTES
        return f"{dt.hour:02d}:{bucket_minute:02d}"

    def _day_type(self, dt: datetime) -> str:
        """Return 'weekday' or 'weekend'."""
        return "weekend" if dt.weekday() >= 5 else "weekday"

    def analyze_door_events(self, events: List[datetime]) -> List[Dict]:
        """
        Analyze door events to find patterns.

        Args:
            events: List of datetime objects for door events

        Returns:
            List of detected patterns
        """
        if len(events) < MIN_OBSERVATIONS:
            return []

        # Group events by day type and time bucket
        weekday_buckets = defaultdict(list)
        weekend_buckets = defaultdict(list)

        for event in events:
            bucket = self._time_bucket(event)
            day_type = self._day_type(event)

            if day_type == "weekday":
                weekday_buckets[bucket].append(event)
            else:
                weekend_buckets[bucket].append(event)

        patterns = []

        # Find weekday patterns
        for bucket, bucket_events in weekday_buckets.items():
            if len(bucket_events) >= MIN_OBSERVATIONS:
                confidence = min(len(bucket_events) / 10, 1.0)  # Max confidence at 10 observations
                patterns.append({
                    "type": "weekday_activity",
                    "time_bucket": bucket,
                    "observations": len(bucket_events),
                    "confidence": confidence,
                    "description": f"Activity around {bucket} on weekdays",
                    "first_observed": min(bucket_events).isoformat(),
                    "last_observed": max(bucket_events).isoformat(),
                })

        # Find weekend patterns
        for bucket, bucket_events in weekend_buckets.items():
            if len(bucket_events) >= MIN_OBSERVATIONS:
                confidence = min(len(bucket_events) / 10, 1.0)
                patterns.append({
                    "type": "weekend_activity",
                    "time_bucket": bucket,
                    "observations": len(bucket_events),
                    "confidence": confidence,
                    "description": f"Activity around {bucket} on weekends",
                    "first_observed": min(bucket_events).isoformat(),
                    "last_observed": max(bucket_events).isoformat(),
                })

        # Detect morning departure pattern (7-10am weekdays)
        morning_events = [
            e for e in events
            if self._day_type(e) == "weekday" and 7 <= e.hour <= 10
        ]
        if len(morning_events) >= MIN_OBSERVATIONS:
            avg_hour = sum(e.hour + e.minute / 60 for e in morning_events) / len(morning_events)
            avg_time = f"{int(avg_hour):02d}:{int((avg_hour % 1) * 60):02d}"
            patterns.append({
                "type": "morning_departure",
                "time_bucket": avg_time,
                "observations": len(morning_events),
                "confidence": min(len(morning_events) / 10, 1.0),
                "description": f"Typically leaves around {avg_time} on weekday mornings",
                "first_observed": min(morning_events).isoformat(),
                "last_observed": max(morning_events).isoformat(),
            })

        # Detect evening arrival pattern (5-8pm weekdays)
        evening_events = [
            e for e in events
            if self._day_type(e) == "weekday" and 17 <= e.hour <= 20
        ]
        if len(evening_events) >= MIN_OBSERVATIONS:
            avg_hour = sum(e.hour + e.minute / 60 for e in evening_events) / len(evening_events)
            avg_time = f"{int(avg_hour):02d}:{int((avg_hour % 1) * 60):02d}"
            patterns.append({
                "type": "evening_arrival",
                "time_bucket": avg_time,
                "observations": len(evening_events),
                "confidence": min(len(evening_events) / 10, 1.0),
                "description": f"Typically arrives around {avg_time} on weekday evenings",
                "first_observed": min(evening_events).isoformat(),
                "last_observed": max(evening_events).isoformat(),
            })

        # Detect night owl pattern (activity after 11pm)
        late_night_events = [e for e in events if e.hour >= 23 or e.hour < 4]
        if len(late_night_events) >= MIN_OBSERVATIONS:
            patterns.append({
                "type": "night_owl",
                "time_bucket": "late",
                "observations": len(late_night_events),
                "confidence": min(len(late_night_events) / 10, 1.0),
                "description": "Often active late at night",
                "first_observed": min(late_night_events).isoformat(),
                "last_observed": max(late_night_events).isoformat(),
            })

        return patterns

    def update_patterns(self, events: List[datetime]):
        """
        Analyze events and update stored patterns.
        Promotes high-confidence patterns to user profile routines.
        """
        new_patterns = self.analyze_door_events(events)

        # Update or add patterns
        for new_p in new_patterns:
            existing = self._find_pattern(new_p["type"], new_p.get("time_bucket"))
            if existing:
                # Update existing pattern
                existing["observations"] = new_p["observations"]
                existing["confidence"] = new_p["confidence"]
                existing["last_observed"] = new_p["last_observed"]
            else:
                # Add new pattern
                self._data["door_patterns"].append(new_p)

        self._data["last_analysis"] = datetime.now().isoformat()
        self._save()

        # Promote high-confidence patterns to routines
        self._promote_patterns()

        return new_patterns

    def _find_pattern(self, pattern_type: str, time_bucket: str = None) -> Optional[Dict]:
        """Find an existing pattern by type and time bucket."""
        for p in self._data["door_patterns"]:
            if p["type"] == pattern_type:
                if time_bucket is None or p.get("time_bucket") == time_bucket:
                    return p
        return None

    def _promote_patterns(self):
        """Promote high-confidence patterns to user profile routines."""
        profile = get_user_profile()

        for pattern in self._data["door_patterns"]:
            if pattern.get("promoted"):
                continue

            if (pattern["confidence"] >= CONFIDENCE_THRESHOLD and
                    pattern["observations"] >= MIN_OBSERVATIONS):

                # Create routine key from pattern type
                routine_key = pattern["type"]

                # Add to profile
                profile.add_routine(
                    key=routine_key,
                    value=pattern["description"],
                    source="door_pattern"
                )

                pattern["promoted"] = True
                pattern["promoted_date"] = datetime.now().isoformat()
                print(f"[PatternDetector] Promoted to routine: {pattern['description']}")

        self._save()

    def get_patterns(self) -> List[Dict]:
        """Get all detected patterns."""
        return self._data["door_patterns"]

    def get_context(self) -> Optional[str]:
        """Format patterns as context for prompts."""
        patterns = [p for p in self._data["door_patterns"] if p["confidence"] >= 0.5]
        if not patterns:
            return None

        lines = ["Observed patterns:"]
        for p in patterns[:5]:  # Top 5
            lines.append(f"- {p['description']} ({p['observations']} observations)")

        return "\n".join(lines)


# Singleton instance
_detector = None


def get_pattern_detector() -> PatternDetector:
    """Get the pattern detector singleton."""
    global _detector
    if _detector is None:
        _detector = PatternDetector()
    return _detector
