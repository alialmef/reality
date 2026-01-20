"""
Weather context.
Fetches current weather for greetings.
"""

import requests
from typing import Optional

from config import config


class WeatherContext:
    """Fetches current weather from OpenWeather API."""

    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

    def get_weather(self) -> Optional[dict]:
        """
        Get current weather.
        Returns None if API key not configured or request fails.
        """
        if not config.OPENWEATHER_API_KEY:
            return None

        try:
            response = requests.get(
                self.BASE_URL,
                params={
                    "q": config.OPENWEATHER_CITY,
                    "appid": config.OPENWEATHER_API_KEY,
                    "units": "imperial",
                },
                timeout=5,
            )
            response.raise_for_status()
            data = response.json()

            return {
                "temp_f": round(data["main"]["temp"]),
                "condition": data["weather"][0]["main"].lower(),
                "description": data["weather"][0]["description"],
            }

        except Exception as e:
            print(f"[Weather] Failed to fetch weather: {e}")
            return None

    def get_weather_description(self) -> Optional[str]:
        """Get a natural language weather description."""
        weather = self.get_weather()
        if not weather:
            return None

        temp = weather["temp_f"]
        condition = weather["condition"]

        # Simple natural language
        if temp > 85:
            temp_desc = "quite hot"
        elif temp > 75:
            temp_desc = "warm"
        elif temp > 60:
            temp_desc = "pleasant"
        elif temp > 45:
            temp_desc = "cool"
        elif temp > 32:
            temp_desc = "cold"
        else:
            temp_desc = "freezing"

        return f"{temp_desc}, {condition}"
