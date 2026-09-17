"""Demonstration entry point for the excel_processor package.

This module provides a deterministic demonstration of the excel_processor
functionality by constructing a sample Sheet, applying filter, sort, aggregate,
and report operations, and returning the results as a dictionary.
"""

from excel_processor import Sheet, filter_rows, sort_rows, aggregate_column, build_report


def run_demo() -> dict:
    """Run a deterministic demonstration of excel_processor operations.

    Constructs a sample Sheet, applies filtering, sorting, aggregation, and
    reporting operations, and returns the results as a dictionary.

    Returns:
        A dictionary containing the results of the demonstration operations.
    """
    # Create a sample sheet from values
    sample_data = [[3, "c"], [1, "a"], [2, "b"], [None, ""]]
    sheet = Sheet.from_values(sample_data)

    # Apply filter operation
    filtered_sheet = filter_rows(
        sheet, 
        lambda row: isinstance(row.values()[0], (int, float)) and row.values()[0] >= 2
    )

    # Apply sort operation
    sorted_sheet = sort_rows(
        Sheet.from_values([[3], [1], [2]]),
        key=lambda row: row.values()[0]
    )

    # Apply aggregate operation
    aggregated_result = aggregate_column(sheet, column=0)

    # Apply report operation
    report_result = build_report(sheet)

    # Return results as a dictionary
    return {
        "filtered_rows": filtered_sheet.to_values(),
        "sorted_rows": sorted_sheet.to_values(),
        "aggregated_column_0": aggregated_result,
        "report": report_result
    }


if __name__ == "__main__":
    # Run the demonstration and print the result
    result = run_demo()
    print(result)