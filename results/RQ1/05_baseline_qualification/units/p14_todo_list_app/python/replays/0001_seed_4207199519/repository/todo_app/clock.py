"""Clock abstraction for deterministic time handling."""

from abc import ABC, abstractmethod
from datetime import date


class Clock(ABC):
    """Abstract base class for time sources."""

    @abstractmethod
    def today(self) -> date:
        """Get the current date.

        Returns:
            date: The current date.
        """


class SystemClock(Clock):
    """Real-time clock using system time."""

    def today(self) -> date:
        """Get the current date from the system.

        Returns:
            date: The current date.
        """
        return date.today()


class FixedClock(Clock):
    """Fixed-date clock for deterministic testing."""

    def __init__(self, fixed: date) -> None:
        """Initialize with a fixed date.

        Args:
            fixed: The fixed date to return from today().
        """
        self.fixed = fixed

    def today(self) -> date:
        """Get the fixed date.

        Returns:
            date: The fixed date.
        """
        return self.fixed