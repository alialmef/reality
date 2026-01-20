"""
Base class for sensors.
All sensor types implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Callable


class BaseSensor(ABC):
    """Abstract base class for sensors."""

    @abstractmethod
    def start(self, callback: Callable[[dict], None]) -> None:
        """
        Start listening for sensor events.

        Args:
            callback: Function to call when sensor triggers.
                      Receives a dict with event details.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop listening for sensor events."""
        pass
