"""Public API exports for the excel_processor package.

This module re-exports all public symbols from the submodules to provide
a canonical interface for users of the excel_processor library.
"""

from .model import Cell, Row, Sheet
from .operations import filter_rows, sort_rows, aggregate_column
from .csv_io import loads_csv, dumps_csv
from .report import build_report

__all__ = [
    "Cell",
    "Row",
    "Sheet",
    "filter_rows",
    "sort_rows",
    "aggregate_column",
    "loads_csv",
    "dumps_csv",
    "build_report",
]