"""Pure functional operations for Excel-like data processing.

This module provides immutable operations on Sheet objects including filtering,
sorting, and column aggregation. All operations return new Sheet instances
without mutating the input.
"""

from typing import List, Callable, Dict, Any
from .model import Sheet, Row


def filter_rows(sheet: Sheet, predicate: Callable[[Row], bool]) -> Sheet:
    """Filter rows from a sheet based on a predicate function.

    Args:
        sheet: The input sheet to filter.
        predicate: A function that takes a Row and returns True if the row
            should be included in the result.

    Returns:
        A new Sheet containing only the rows for which predicate(row) is True.
        The order of rows is preserved (stable).
    """
    filtered_rows = [row for row in sheet._rows if predicate(row)]
    return Sheet(filtered_rows)


def sort_rows(
    sheet: Sheet, key: Callable[[Row], Any], reverse: bool = False
) -> Sheet:
    """Sort rows from a sheet based on a key function.

    Args:
        sheet: The input sheet to sort.
        key: A function that takes a Row and returns a value to sort by.
        reverse: If True, sort in descending order. Default is False.

    Returns:
        A new Sheet with rows sorted according to the key function.
        The order is stable.
    """
    sorted_rows = sorted(sheet._rows, key=key, reverse=reverse)
    return Sheet(sorted_rows)


def aggregate_column(sheet: Sheet, column: int) -> Dict[str, Any]:
    """Aggregate statistics for a specific column in a sheet.

    Args:
        sheet: The input sheet to aggregate.
        column: The zero-based index of the column to aggregate.

    Returns:
        A dictionary containing:
        - count: Total number of rows in the sheet.
        - missing: Number of cells that are None or empty string.
        - numeric_count: Number of numeric values (int/float, excluding bool).
        - sum: Sum of numeric values, or 0 if none.
        - min: Minimum numeric value, or None if none.
        - max: Maximum numeric value, or None if none.

    Raises:
        IndexError: If column index is out of range.
    """
    if column < 0 or column >= sheet.column_count():
        raise IndexError("Column index out of range")

    count = sheet.row_count()
    missing = 0
    numeric_count = 0
    total_sum = 0
    min_val = None
    max_val = None

    for row in sheet._rows:
        cell_value = row._cells[column].value
        # Check for missing values (None or empty string)
        if cell_value is None or cell_value == "":
            missing += 1
        elif isinstance(cell_value, (int, float)) and not isinstance(cell_value, bool):
            # Numeric values (excluding bool)
            numeric_count += 1
            total_sum += cell_value
            if min_val is None or cell_value < min_val:
                min_val = cell_value
            if max_val is None or cell_value > max_val:
                max_val = cell_value

    return {
        "count": count,
        "missing": missing,
        "numeric_count": numeric_count,
        "sum": total_sum,
        "min": min_val,
        "max": max_val,
    }