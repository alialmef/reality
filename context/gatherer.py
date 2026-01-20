"""
Context gatherer.
Assembles all available context for greeting generation.
"""

from datetime import datetime
from typing import Optional

from context.presence import PresenceTracker
from context.weather import WeatherContext
from config import config


class ContextGatherer:
    """Gathers all context needed for Alfred's greeting."""

    def __init__(self):
        self.presence = PresenceTracker()
        self.weather = WeatherContext()

    def gather(self) -> dict:
        """
        Gather all context for a door event.
        Returns a dict with everything Alfred needs to know.
        """
        now = datetime.now()

        # Determine if this is arriving or leaving
        # If we're already home and door opens within 10 min of arrival, we're leaving
        is_leaving = False
        if self.presence.is_home and self.presence.last_arrival:
            seconds_since_arrival = (now - self.presence.last_arrival).total_seconds()
            if seconds_since_arrival < 600:  # 10 minutes
                is_leaving = True

        if is_leaving:
            # Record departure
            self.presence.record_departure()
            seconds_away = None
        else:
            # Record arrival and get absence info
            arrival_info = self.presence.record_arrival()
            seconds_away = arrival_info.get("seconds_away")

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

        # Absence context
        absence_description = self.presence.get_absence_description(seconds_away)
        should_greet = (
            seconds_away is None or seconds_away >= config.MIN_ABSENCE_SECONDS
        )

        # Weather (optional)
        weather_description = self.weather.get_weather_description()

        return {
            "time_of_day": time_of_day,
            "hour": hour,
            "day_name": day_name,
            "is_weekend": is_weekend,
            "seconds_away": seconds_away,
            "absence_description": absence_description,
            "should_greet": should_greet,
            "is_leaving": is_leaving,
            "weather": weather_description,
            "timestamp": now.isoformat(),
        }
