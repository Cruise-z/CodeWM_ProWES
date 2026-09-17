"""Immutable calculation history."""

from typing import Final, List, Tuple


HistoryRecord = Tuple[str, float]


class History:
    """Immutable append-only history.

    Records are stored as (expression, result) tuples.
    """

    _records: Final[List[HistoryRecord]]

    def __init__(self) -> None:
        """Initialize an empty history."""
        self._records = []

    def add(self, expression: str, result: float) -> None:
        """Add a new record to the history.

        Args:
            expression: The expression that was evaluated.
            result: The result of the evaluation.
        """
        self._records.append((expression, result))

    def records(self) -> List[HistoryRecord]:
        """Get a copy of all records in the history.

        Returns:
            A list of (expression, result) tuples.
        """
        return self._records.copy()

    def __len__(self) -> int:
        """Get the number of records in the history.

        Returns:
            The number of records.
        """
        return len(self._records)