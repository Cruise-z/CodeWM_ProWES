"""Model definitions for Excel-like data structures.

This module provides the foundational types for working with spreadsheet data:
Cell, Row, and Sheet. These types are designed with defensive copying and
snapshot semantics to ensure data integrity and predictable behavior.
"""

from typing import List, Optional, Any


class Cell:
    """A mutable cell that holds a value.

    Attributes:
        value: The value stored in the cell, which can be any object or None.
    """

    def __init__(self, value: Optional[Any] = None) -> None:
        """Initialize a Cell with an optional value.

        Args:
            value: The initial value for the cell. Defaults to None.
        """
        self.value = value


class Row:
    """A row of cells with defensive copying and snapshot semantics.

    This class represents a row in a spreadsheet, containing a list of Cell
    objects. It provides a snapshot view of the values in the row without
    exposing internal mutable state directly.

    Attributes:
        _cells: A defensive copy of the list of cells in this row.
    """

    def __init__(self, cells: List[Cell]) -> None:
        """Initialize a Row with a list of cells.

        Args:
            cells: A list of Cell objects representing the contents of the row.
        """
        # Defensive copy to prevent external modification
        self._cells = list(cells)

    def values(self) -> List[Any]:
        """Get a snapshot list of values from the cells in this row.

        Returns:
            A list containing the value of each cell in order.
        """
        return [cell.value for cell in self._cells]


class Sheet:
    """A sheet containing rows of data with defensive copying and snapshot APIs.

    This class represents a two-dimensional grid of data similar to a spreadsheet.
    It supports construction from primitive values, indexing operations with
    validation, and snapshot views of the data.

    Attributes:
        _rows: A defensive copy of the list of rows in this sheet.
    """

    def __init__(self, rows: List[Row]) -> None:
        """Initialize a Sheet with a list of rows.

        Args:
            rows: A list of Row objects representing the content of the sheet.
        """
        # Defensive copy to prevent external modification
        self._rows = list(rows)

    @classmethod
    def from_values(cls, values: List[List[Any]]) -> 'Sheet':
        """Construct a Sheet from a list of lists of values.

        Args:
            values: A list of lists where each inner list represents a row of
                values. All non-empty rows must have the same length (ragged check).

        Returns:
            A new Sheet instance constructed from the provided values.

        Raises:
            ValueError: If there are non-empty rows with different lengths.
        """
        if not values:
            return cls([])

        # Validate that all non-empty rows have the same length
        non_empty_rows = [r for r in values if r]
        if non_empty_rows:
            first_row_length = len(non_empty_rows[0])
            if not all(len(r) == first_row_length for r in non_empty_rows):
                raise ValueError("Ragged rows detected")

        # Create cells and rows
        rows = []
        for row_values in values:
            cells = [Cell(value) for value in row_values]
            rows.append(Row(cells))

        return cls(rows)

    def to_values(self) -> List[List[Any]]:
        """Get a deep snapshot of the sheet's data as a list of lists.

        Returns:
            A list of lists where each inner list is a snapshot of a row's values.
        """
        return [row.values() for row in self._rows]

    def row_count(self) -> int:
        """Get the number of rows in the sheet.

        Returns:
            The number of rows in the sheet.
        """
        return len(self._rows)

    def column_count(self) -> int:
        """Get the number of columns in the sheet.

        Returns:
            The number of columns in the sheet, or 0 if there are no rows.
        """
        if not self._rows:
            return 0
        return len(self._rows[0]._cells)

    def get_cell(self, row: int, column: int) -> Cell:
        """Get a specific cell from the sheet.

        Args:
            row: The zero-based index of the row.
            column: The zero-based index of the column.

        Returns:
            The Cell object at the specified position.

        Raises:
            IndexError: If the indices are out of range or negative.
        """
        if row < 0 or column < 0:
            raise IndexError("Indices must be non-negative")
        if row >= len(self._rows) or column >= len(self._rows[0]._cells):
            raise IndexError("Index out of range")
        return self._rows[row]._cells[column]

    def set_cell(self, row: int, column: int, value: Any) -> None:
        """Set the value of a specific cell in the sheet.

        Args:
            row: The zero-based index of the row.
            column: The zero-based index of the column.
            value: The new value to assign to the cell.

        Raises:
            IndexError: If the indices are out of range or negative.
        """
        if row < 0 or column < 0:
            raise IndexError("Indices must be non-negative")
        if row >= len(self._rows) or column >= len(self._rows[0]._cells):
            raise IndexError("Index out of range")
        self._rows[row]._cells[column].value = value