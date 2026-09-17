"""Progress tracking and cancellation support."""

from typing import Optional, Callable, List


class CancellationToken:
    """A token that can be used to signal cancellation."""

    def __init__(self) -> None:
        """Initialize a cancellation token."""
        self._cancelled = False

    def cancel(self) -> None:
        """Signal that the operation should be cancelled."""
        self._cancelled = True

    def is_cancelled(self) -> bool:
        """Check if the operation has been cancelled."""
        return self._cancelled


class Progress:
    """Track download progress with optional total bytes."""

    def __init__(self, total: Optional[int] = None) -> None:
        """Initialize progress tracker.

        Args:
            total: The total number of bytes to transfer, or None if unknown.
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
        """Get the total number of bytes to transfer."""
        return self._total

    def update(self, delta: int) -> None:
        """Update the transferred byte count.

        Args:
            delta: The number of bytes transferred since the last update.

        Raises:
            ValueError: If delta is negative.
        """
        if delta < 0:
            raise ValueError("Delta must not be negative")

        # Clamp the transferred amount at the total
        if self._total is not None:
            self._transferred = min(self._transferred + delta, self._total)
        else:
            self._transferred += delta

        # Notify all listeners
        for listener in self._listeners:
            listener(self._transferred, self._total)

    def percent(self) -> Optional[float]:
        """Calculate the completion percentage.

        Returns:
            The percentage complete, or None if total is unknown.
        """
        if self._total is None:
            return None
        return (self._transferred / self._total) * 100

    def add_listener(self, callback: Callable[[int, Optional[int]], None]) -> None:
        """Add a listener to be notified of progress updates.

        Args:
            callback: A function that takes (transferred, total) as arguments.
        """
        self._listeners.append(callback)