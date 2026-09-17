"""Progress tracking and cancellation utilities."""

from typing import Optional, Callable, List


class CancellationToken:
    """A token that can be used to signal cancellation."""

    def __init__(self) -> None:
        """Initialize a cancellation token."""
        self._cancelled = False

    def cancel(self) -> None:
        """Cancel the token."""
        self._cancelled = True

    def is_cancelled(self) -> bool:
        """
        Check if the token has been cancelled.

        Returns:
            True if cancelled, False otherwise.
        """
        return self._cancelled


class Progress:
    """Track progress of a transfer operation."""

    def __init__(self, total: Optional[int] = None) -> None:
        """
        Initialize progress tracker.

        Args:
            total: Total bytes to transfer, or None if unknown.
        """
        self._transferred = 0
        self._total = total
        self._listeners: List[Callable[[int, Optional[int]], None]] = []

    @property
    def transferred(self) -> int:
        """
        Get the number of bytes transferred.

        Returns:
            The number of bytes transferred.
        """
        return self._transferred

    @property
    def total(self) -> Optional[int]:
        """
        Get the total number of bytes to transfer.

        Returns:
            The total bytes, or None if unknown.
        """
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
            raise ValueError("Delta must be non-negative")

        # Clamp at total if total is known
        if self._total is not None:
            self._transferred = min(self._transferred + delta, self._total)
        else:
            self._transferred += delta

        # Notify listeners
        for listener in self._listeners:
            listener(self._transferred, self._total)

    def percent(self) -> Optional[float]:
        """
        Calculate the percentage of transfer completed.

        Returns:
            The percentage completed, or None if total is unknown.
        """
        if self._total is None:
            return None
        return (self._transferred / self._total) * 100

    def add_listener(self, callback: Callable[[int, Optional[int]], None]) -> None:
        """
        Add a listener to be notified on progress updates.

        Args:
            callback: A function that takes (transferred, total) as arguments.
        """
        self._listeners.append(callback)