"""Deterministic headless clock abstraction and manual tick source.

This module provides a ManualClock class that serves as a deterministic,
headless clock for the video player domain. It allows for precise control
of time progression through manual tick events, making it suitable for
testing and scenarios where real-time dependencies are undesirable.
"""

from typing import Callable, List
from .errors import ValidationError


class ManualClock:
    """A deterministic, headless clock implementation for testing and simulation.

    This clock does not rely on system time or real-world timing. Instead,
    it advances time only when explicitly told to via the tick method.
    Listeners can register to receive notifications when the clock ticks.
    """

    def __init__(self) -> None:
        """Initialize a new ManualClock instance.

        The clock starts at time 0.0 and has no listeners initially.
        """
        self._time: float = 0.0
        self._listeners: List[Callable[[float], None]] = []

    def now(self) -> float:
        """Get the current time of the clock.

        Returns:
            The current time in seconds since the clock was initialized.
        """
        return self._time

    def add_tick_listener(self, fn: Callable[[float], None]) -> None:
        """Add a listener function to be called on each tick.

        Args:
            fn: A callable that accepts a single float argument (the delta time).
                The function will be called synchronously during tick() in
                registration order.

        Note:
            Adding the same function multiple times is allowed and will result
            in multiple invocations during each tick.
        """
        self._listeners.append(fn)

    def remove_tick_listener(self, fn) -> None:
        """Remove a previously added tick listener.

        Args:
            fn: The listener function to remove.

        Note:
            If the function was not previously added, this method does nothing.
        """
        try:
            self._listeners.remove(fn)
        except ValueError:
            # Function was not in the list, ignore
            pass

    def tick(self, delta_seconds: float) -> None:
        """Advance the clock by the specified delta time.

        Args:
            delta_seconds: The amount of time to advance the clock, in seconds.
                          Must be a positive number greater than zero.

        Raises:
            ValidationError: If delta_seconds is not a positive number.
        """
        if not isinstance(delta_seconds, (int, float)):
            raise ValidationError("Delta time must be a number")
        if delta_seconds <= 0:
            raise ValidationError("Delta time must be positive")

        self._time += delta_seconds
        # Notify all listeners synchronously
        for listener in self._listeners:
            listener(delta_seconds)