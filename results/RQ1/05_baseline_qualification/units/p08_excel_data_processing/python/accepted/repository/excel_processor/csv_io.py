"""CSV I/O operations for Excel-like data processing.

This module provides functions to load and dump Excel-like data from/to CSV
strings. All cell values are preserved as strings, and ragged rows are
detected and rejected.
"""

import csv
import io
from typing import List, Any
from .model import Sheet, Cell, Row


def loads_csv(text: str) -> Sheet:
    """Load a Sheet from a CSV-formatted string.

    Args:
        text: A string containing CSV data with a header row.

    Returns:
        A Sheet instance constructed from the CSV data.

    Raises:
        ValueError: If the CSV contains ragged rows (inconsistent column counts).
    """
    # Use StringIO to treat the string as a file-like object
    reader = csv.reader(io.StringIO(text))
    
    # Read all rows
    rows = list(reader)
    
    # Handle empty CSV
    if not rows:
        return Sheet([])
    
    # Validate that all non-empty rows have the same length as the first row
    first_row_length = len(rows[0])
    for i, row in enumerate(rows):
        if row and len(row) != first_row_length:
            raise ValueError(f"Ragged rows detected: row {i} has {len(row)} columns, "
                           f"expected {first_row_length}")
    
    # Convert to Sheet format
    sheet_rows = []
    for row_data in rows:
        cells = [Cell(value) for value in row_data]
        sheet_rows.append(Row(cells))
    
    return Sheet(sheet_rows)


def dumps_csv(sheet: Sheet) -> str:
    """Dump a Sheet to a CSV-formatted string.

    Args:
        sheet: The Sheet to serialize to CSV format.

    Returns:
        A string containing the CSV representation of the sheet.
    """
    # Get the values from the sheet
    values = sheet.to_values()
    
    # Use StringIO to capture the CSV output
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write all rows
    writer.writerows(values)
    
    # Get the CSV string and return it
    return output.getvalue()