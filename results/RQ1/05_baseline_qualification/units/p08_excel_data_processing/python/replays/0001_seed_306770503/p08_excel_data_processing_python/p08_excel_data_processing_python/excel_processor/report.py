"""Reporting functionality for Excel-like data processing.

This module provides functions to generate reports about Sheet objects,
including dimension information and missing cell counts.
"""

from typing import Dict, Any
from .model import Sheet


def build_report(sheet: Sheet) -> Dict[str, Any]:
    """Build a report with metadata about a sheet's structure and content.

    Args:
        sheet: The sheet to analyze and generate a report for.

    Returns:
        A dictionary containing:
        - row_count: The number of rows in the sheet.
        - column_count: The number of columns in the sheet.
        - missing_cells: The count of cells that are None or empty string.
    """
    row_count = sheet.row_count()
    column_count = sheet.column_count()
    
    missing_cells = 0
    
    # Count missing cells (None or empty string)
    for row in sheet._rows:
        for cell in row._cells:
            if cell.value is None or cell.value == "":
                missing_cells += 1
                
    return {
        "row_count": row_count,
        "column_count": column_count,
        "missing_cells": missing_cells,
    }