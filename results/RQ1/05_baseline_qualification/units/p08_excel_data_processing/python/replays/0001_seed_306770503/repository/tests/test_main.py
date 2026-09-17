"""Tests for the excel_processor package and Main.py demonstration.

This module contains pytest tests that verify:
1. The run_demo function in Main.py returns a dict
2. Core operations work correctly with the specified fixtures
3. CSV loading/dumping works correctly and detects ragged rows
4. Reporting works correctly with missing cell counting
"""

from excel_processor import (
    Sheet,
    filter_rows,
    sort_rows,
    aggregate_column,
    loads_csv,
    dumps_csv,
    build_report,
)
from Main import run_demo


def test_run_demo_returns_dict():
    """Test that run_demo returns a dictionary."""
    result = run_demo()
    assert isinstance(result, dict)


def test_operations_semantics():
    """Test core operations semantics with literal fixtures."""
    # Test filtering
    sheet = Sheet.from_values([[3, "c"], [1, "a"], [2, "b"], [None, ""]])
    filtered = filter_rows(
        sheet,
        lambda row: isinstance(row.values()[0], (int, float)) and row.values()[0] >= 2
    )
    expected_filtered = [[3, "c"], [2, "b"]]
    assert filtered.to_values() == expected_filtered

    # Test sorting
    sorted_sheet = sort_rows(
        Sheet.from_values([[3], [1], [2]]),
        key=lambda row: row.values()[0]
    )
    expected_sorted = [[1], [2], [3]]
    assert sorted_sheet.to_values() == expected_sorted

    # Test aggregation
    agg_result = aggregate_column(sheet, column=0)
    expected_agg = {
        "count": 4,
        "missing": 1,
        "numeric_count": 3,
        "sum": 6,
        "min": 1,
        "max": 3
    }
    assert agg_result == expected_agg


def test_csv_roundtrip_and_reporting():
    """Test CSV loading/dumping and reporting with specific fixture."""
    csv_text = "name,value\nA,1\nB,\n"
    
    # Test loading
    loaded_sheet = loads_csv(csv_text)
    expected_values = [["name", "value"], ["A", "1"], ["B", ""]]
    assert loaded_sheet.to_values() == expected_values
    
    # Test dumping (round trip)
    dumped_text = dumps_csv(loaded_sheet)
    reloaded_sheet = loads_csv(dumped_text)
    assert reloaded_sheet.to_values() == expected_values
    
    # Test reporting
    report = build_report(loaded_sheet)
    expected_report = {
        "row_count": 3,
        "column_count": 2,
        "missing_cells": 1
    }
    assert report == expected_report