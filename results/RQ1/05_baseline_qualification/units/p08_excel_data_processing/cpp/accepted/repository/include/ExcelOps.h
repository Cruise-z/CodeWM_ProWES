#ifndef EXCEL_OPS_H
#define EXCEL_OPS_H

#include <string>
#include <vector>
#include <functional>
#include <optional>
#include <ostream>
#include <stdexcept>

#include "ExcelCore.h"

namespace excel {

/**
 * Specifies the ordering of missing values during sorting.
 */
enum class MissingOrder {
    First,
    Last
};

/**
 * Represents a sorting key for a column.
 */
struct SortKey {
    std::string column;
    bool ascending = true;
    MissingOrder missing = MissingOrder::Last;
};

/**
 * Represents a sorting specification with multiple keys.
 */
struct SortSpec {
    std::vector<SortKey> keys;
};

/**
 * Represents a report of processing operations performed on a sheet.
 */
class ProcessingReport {
public:
    size_t rows_read = 0;
    size_t rows_kept = 0;
    size_t rows_dropped = 0;
    size_t invalid_cells = 0;
    size_t missing_cells = 0;
    std::vector<std::string> operations;

    /**
     * Adds an operation to the report.
     * @param operation The operation to add.
     */
    void addOperation(const std::string& operation);

    /**
     * Merges another report into this one.
     * @param other The other report to merge.
     */
    void merge(const ProcessingReport& other);

    /**
     * Converts the report to a string representation.
     * @return A string summarizing the report.
     */
    std::string toString() const;
};

/**
 * Selects columns from a sheet by their names.
 * @param sheet The sheet to select columns from.
 * @param columnNames The names of the columns to select.
 * @param report The report to update with operation details (optional).
 * @return A new sheet containing only the selected columns.
 */
Sheet selectColumnsByNames(const Sheet& sheet, const std::vector<std::string>& columnNames, ProcessingReport* report = nullptr);

/**
 * Selects columns from a sheet by their indices.
 * @param sheet The sheet to select columns from.
 * @param indices The indices of the columns to select.
 * @param report The report to update with operation details (optional).
 * @return A new sheet containing only the selected columns.
 */
Sheet selectColumnsByIndices(const Sheet& sheet, const std::vector<size_t>& indices, ProcessingReport* report = nullptr);

/**
 * Type alias for a row predicate function.
 */
using RowPredicate = std::function<bool(const Sheet&, size_t)>;

/**
 * Filters rows from a sheet based on a predicate.
 * @param sheet The sheet to filter.
 * @param predicate The predicate to apply to each row.
 * @param report The report to update with operation details (optional).
 * @return A new sheet containing only the rows that satisfy the predicate.
 */
Sheet filterRows(const Sheet& sheet, const RowPredicate& predicate, ProcessingReport* report = nullptr);

/**
 * Creates a predicate that checks if a numeric column value is greater than a threshold.
 * @param column The name of the column to check.
 * @param threshold The threshold value.
 * @param reportForInvalidsOrNullptr The report to update with invalid cell counts (optional).
 * @return A row predicate.
 */
RowPredicate makeNumericGreaterThan(const std::string& column, double threshold, ProcessingReport* reportForInvalidsOrNullptr = nullptr);

/**
 * Sorts rows in a sheet according to a sort specification.
 * @param sheet The sheet to sort.
 * @param spec The sort specification.
 * @param report The report to update with operation details (optional).
 * @return A new sheet with sorted rows.
 */
Sheet sortRows(const Sheet& sheet, const SortSpec& spec, ProcessingReport* report = nullptr);

/**
 * Represents the result of aggregating a numeric column.
 */
struct AggregationResult {
    size_t count_valid = 0;
    size_t count_missing = 0;
    size_t count_invalid = 0;
    double sum = 0.0;
    std::optional<double> average;
};

/**
 * Aggregates a numeric column in a sheet.
 * @param sheet The sheet to aggregate.
 * @param column The name of the column to aggregate.
 * @param report The report to update with operation details (optional).
 * @return The aggregation result.
 */
AggregationResult aggregateNumeric(const Sheet& sheet, const std::string& column, ProcessingReport* report = nullptr);

} // namespace excel

#endif // EXCEL_OPS_H