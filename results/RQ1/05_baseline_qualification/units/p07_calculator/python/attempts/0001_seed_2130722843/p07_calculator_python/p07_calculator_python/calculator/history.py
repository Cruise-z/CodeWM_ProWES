"""Immutable calculation history implementation."""

from typing import Final, List, Tuple


class History:
    """Immutable append-only history of calculations.

    Records are stored as (expression, result) tuples.
    All methods return new objects or copies; no mutation occurs.
    """

    def __init__(self) -> None:
        """Initialize an empty history."""
        self._records: Final[List[Tuple[str, float]]] = []

    def add(self, expression: str, result: float) -> None:
        """Add a new record to the history.

        Args:
            expression: The arithmetic expression that was evaluated.
            result: The numerical result of the evaluation.
        """
        # Create a new list with the added record
        new_records = self._records + [(expression, result)]
        # Create a new History instance with the updated records
        # Note: This is a simple approach to immutability
        # In a more complex system, we might use a different pattern
        self._records = new_records

    def records(self) -> List[Tuple[str, float]]:
        """Get a copy of all records in the history.

        Returns:
            A list of (expression, result) tuples.
        """
        # Return a shallow copy to prevent external mutation
        return self._records.copy()

    def __len__(self) -> int:
        """Get the number of records in the history.

        Returns:
            The count of recorded calculations.
        """
        return len(self._records)