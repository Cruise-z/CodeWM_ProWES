"""Progress tracking and cancellation utilities."""

from typing import Optional, Callable, List


class Progress:
    """Track transfer progress with optional total size and listener notifications."""

    def __init__(self, total: Optional[int] = None) -> None:
        """
        Initialize progress tracker.

        Args:
            total: Total bytes expected, or None if unknown.
        """
        self._transferred = 0
        self._total = total
        self._listeners: List[Callable[[int, Optional[int]], None]] = []

    @property
    def transferred(self) -> int:
        """Get the number of bytes transferred."""
        return self._transferred

    @property
    def total(self) -> Optional[int]:
        """Get the total number of bytes expected."""
        return self._total

    def update(self, delta: int) -> None:
        """
        Update the transferred byte count.

        Args:
            delta: Number of bytes to add to transferred count.

        Raises:
            ValueError: If delta is negative.
        """
        if delta < 0:
            raise ValueError("Delta must not be negative")
        
        self._transferred += delta
        if self._total is not None:
            self._transferred = min(self._transferred, self._total)
        
        # Notify listeners
        for listener in self._listeners:
            listener(self._transferred, self._total)

    def percent(self) -> Optional[float]:
        """
        Calculate completion percentage.

        Returns:
            Completion percentage as float between 0 and 100, or None if total is unknown.
        """
        if self._total is None:
            return None
        return (self._transferred / self._total) * 100

    def add_listener(self, callback: Callable[[int, Optional[int]], None]) -> None:
        """
        Add a progress listener.

        Args:
            callback: Function to call with (transferred, total) on updates.
        """
        self._listeners.append(callback)


class CancellationToken:
    """A token that can be used to signal cancellation."""

    def __init__(self) -> None:
        """Initialize a cancellation token."""
        self._cancelled = False

    def cancel(self) -> None:
        """Mark the token as cancelled."""
        self._cancelled = True

    def is_cancelled(self) -> bool:
        """
        Check if the token has been cancelled.

        Returns:
            True if cancelled, False otherwise.
        """
        return self._cancelled