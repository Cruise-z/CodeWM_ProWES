"""Deterministic clock implementation for the CRUD system."""

from typing import Optional


class FixedClock:
    """A deterministic clock that returns a current value and advances by a step."""

    def __init__(self, base: float = 100.0, step: float = 10.0) -> None:
        """Initialize the clock with a base time and step size.

        Args:
            base: The initial time value.
            step: The amount to advance the clock after each call to now().
        """
        self._current = base
        self._step = step

    def now(self) -> float:
        """Get the current time and advance the clock by the step amount.

        Returns:
            The current time value before advancing.
        """
        current_time = self._current
        self._current += self._step
        return current_time