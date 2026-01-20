"""
Context gatherer.
Assembles all available context for greeting generation.
"""

from datetime import datetime

from context.presence import PresenceTracker
from context.weather import WeatherContext


class ContextGatherer:
    """Gathers all context needed for Alfred's greeting."""

    def __init__(self):
        self.presence = PresenceTracker()
        self.weather = WeatherContext()

    def gather(self) -> dict:
        """
        Gather all context for a door event.
        Returns raw data - let Claude decide what it means.
        """
        now = datetime.now()

        # Record this door event and get timing
        event_info = self.presence.record_door_event()
        seconds_since_last = event_info["seconds_since_last"]

        # Time context
        hour = now.hour
        if hour < 6:
            time_of_day = "late night"
        elif hour < 12:
            time_of_day = "morning"
        elif hour < 17:
            time_of_day = "afternoon"
        elif hour < 21:
            time_of_day = "evening"
        else:
            time_of_day = "night"

        # Day context
        day_name = now.strftime("%A")
        is_weekend = now.weekday() >= 5

        # Time description
        time_description = self.presence.get_time_description(seconds_since_last)

        # Weather (optional)
        weather_description = self.weather.get_weather_description()

        return {
            "time_of_day": time_of_day,
            "hour": hour,
            "day_name": day_name,
            "is_weekend": is_weekend,
            "seconds_since_last_door_event": seconds_since_last,
            "time_since_last_description": time_description,
            "weather": weather_description,
            "timestamp": now.isoformat(),
        }
