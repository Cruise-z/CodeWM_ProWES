#include "ExcelOps.h"
#include <algorithm>
#include <cctype>
#include <sstream>
#include <iomanip>

namespace excel {

// ProcessingReport implementation
void ProcessingReport::addOperation(const std::string& operation) {
    operations.push_back(operation);
}

void ProcessingReport::merge(const ProcessingReport& other) {
    rows_read += other.rows_read;
    rows_kept += other.rows_kept;
    rows_dropped += other.rows_dropped;
    invalid_cells += other.invalid_cells;
    missing_cells += other.missing_cells;
    operations.insert(operations.end(), other.operations.begin(), other.operations.end());
}

std::string ProcessingReport::toString() const {
    std::ostringstream oss;
    oss << "Processing Report:\n";
    oss << "  Rows read: " << rows_read << "\n";
    oss << "  Rows kept: " << rows_kept << "\n";
    oss << "  Rows dropped: " << rows_dropped << "\n";
    oss << "  Invalid cells: " << invalid_cells << "\n";
    oss << "  Missing cells: " << missing_cells << "\n";
    oss << "  Operations:\n";
    for (const auto& op : operations) {
        oss << "    - " << op << "\n";
    }
    return oss.str();
}

// Column selection implementations
Sheet selectColumnsByNames(const Sheet& sheet, const std::vector<std::string>& columnNames, ProcessingReport* report) {
    std::vector<size_t> indices;
    indices.reserve(columnNames.size());
    
    for (const auto& name : columnNames) {
        indices.push_back(sheet.columnIndex(name));
    }
    
    Sheet result = sheet.cloneWithSubsetColumns(indices);
    
    if (report) {
        std::ostringstream oss;
        oss << "Selected columns: ";
        for (size_t i = 0; i < columnNames.size(); ++i) {
            if (i > 0) oss << ", ";
            oss << columnNames[i];
        }
        report->addOperation(oss.str());
        report->rows_read = sheet.rowCount();
        report->rows_kept = result.rowCount();
    }
    
    return result;
}

Sheet selectColumnsByIndices(const Sheet& sheet, const std::vector<size_t>& indices, ProcessingReport* report) {
    Sheet result = sheet.cloneWithSubsetColumns(indices);
    
    if (report) {
        std::ostringstream oss;
        oss << "Selected columns by indices: ";
        for (size_t i = 0; i < indices.size(); ++i) {
            if (i > 0) oss << ", ";
            oss << indices[i];
        }
        report->addOperation(oss.str());
        report->rows_read = sheet.rowCount();
        report->rows_kept = result.rowCount();
    }
    
    return result;
}

// Filtering implementation
Sheet filterRows(const Sheet& sheet, const RowPredicate& predicate, ProcessingReport* report) {
    Sheet result(sheet.getName(), sheet.getHeaders());
    
    size_t kept = 0;
    size_t dropped = 0;
    
    for (size_t i = 0; i < sheet.rowCount(); ++i) {
        if (predicate(sheet, i)) {
            std::vector<std::string> rowValues;
            rowValues.reserve(sheet.columnCount());
            for (size_t j = 0; j < sheet.columnCount(); ++j) {
                rowValues.push_back(sheet.cell(i, j).asString());
            }
            result.appendRow(rowValues);
            kept++;
        } else {
            dropped++;
        }
    }
    
    if (report) {
        report->addOperation("Filtered rows");
        report->rows_read = sheet.rowCount();
        report->rows_kept = kept;
        report->rows_dropped = dropped;
    }
    
    return result;
}

// Numeric predicate implementation
RowPredicate makeNumericGreaterThan(const std::string& column, double threshold, ProcessingReport* reportForInvalidsOrNullptr) {
    return [column, threshold, reportForInvalidsOrNullptr](const Sheet& sheet, size_t rowIndex) -> bool {
        size_t colIndex = sheet.columnIndex(column);
        const Cell& cell = sheet.cell(rowIndex, colIndex);
        
        if (cell.isMissing()) {
            if (reportForInvalidsOrNullptr) {
                reportForInvalidsOrNullptr->missing_cells++;
            }
            return false; // Treat missing as false for filtering
        }
        
        auto maybeValue = cell.parseDouble();
        if (!maybeValue) {
            if (reportForInvalidsOrNullptr) {
                reportForInvalidsOrNullptr->invalid_cells++;
            }
            return false; // Treat invalid as false for filtering
        }
        
        return *maybeValue > threshold;
    };
}

// Sorting implementation
Sheet sortRows(const Sheet& sheet, const SortSpec& spec, ProcessingReport* report) {
    Sheet result(sheet.getName(), sheet.getHeaders());
    
    // Copy rows to result
    for (size_t i = 0; i < sheet.rowCount(); ++i) {
        std::vector<std::string> rowValues;
        rowValues.reserve(sheet.columnCount());
        for (size_t j = 0; j < sheet.columnCount(); ++j) {
            rowValues.push_back(sheet.cell(i, j).asString());
        }
        result.appendRow(rowValues);
    }
    
    // Prepare comparison function
    auto compareRows = [&sheet, &spec](size_t rowIndexA, size_t rowIndexB) -> bool {
        for (const auto& key : spec.keys) {
            size_t colIndex = sheet.columnIndex(key.column);
            const Cell& cellA = sheet.cell(rowIndexA, colIndex);
            const Cell& cellB = sheet.cell(rowIndexB, colIndex);
            
            // Handle missing values
            bool missingA = cellA.isMissing();
            bool missingB = cellB.isMissing();
            
            if (missingA && missingB) {
                // Both missing, maintain relative order (stable sort)
                continue;
            }
            
            if (missingA) {
                // A is missing, B is not
                return key.missing == MissingOrder::First;
            }
            
            if (missingB) {
                // B is missing, A is not
                return key.missing != MissingOrder::First;
            }
            
            // Both non-missing, compare values
            // Try numeric comparison first
            auto valA = cellA.parseDouble();
            auto valB = cellB.parseDouble();
            
            if (valA && valB) {
                // Both are numeric, compare numerically
                if (*valA < *valB) {
                    return key.ascending;
                } else if (*valA > *valB) {
                    return !key.ascending;
                }
                // Equal, continue to next key
                continue;
            }
            
            // At least one is not numeric, compare as strings
            std::string strA = cellA.asString();
            std::string strB = cellB.asString();
            
            if (strA < strB) {
                return key.ascending;
            } else if (strA > strB) {
                return !key.ascending;
            }
            // Equal, continue to next key
        }
        
        // All keys compared equal, maintain original order (stable sort)
        return false;
    };
    
    // Sort rows using stable sort to maintain relative order for equal elements
    std::vector<size_t> indices(result.rowCount());
    for (size_t i = 0; i < indices.size(); ++i) {
        indices[i] = i;
    }
    std::stable_sort(indices.begin(), indices.end(), compareRows);
    
    // Reorder rows in result according to sorted indices
    Sheet sortedSheet(sheet.getName(), sheet.getHeaders());
    for (size_t idx : indices) {
        std::vector<std::string> rowValues;
        rowValues.reserve(sheet.columnCount());
        for (size_t j = 0; j < sheet.columnCount(); ++j) {
            rowValues.push_back(result.cell(idx, j).asString());
        }
        sortedSheet.appendRow(rowValues);
    }
    
    if (report) {
        std::ostringstream oss;
        oss << "Sorted rows by ";
        for (size_t i = 0; i < spec.keys.size(); ++i) {
            if (i > 0) oss << ", ";
            oss << spec.keys[i].column;
            if (!spec.keys[i].ascending) oss << " DESC";
            if (spec.keys[i].missing == MissingOrder::First) oss << " (missing first)";
        }
        report->addOperation(oss.str());
        report->rows_read = sheet.rowCount();
        report->rows_kept = sortedSheet.rowCount();
    }
    
    return sortedSheet;
}

// Aggregation implementation
AggregationResult aggregateNumeric(const Sheet& sheet, const std::string& column, ProcessingReport* report) {
    AggregationResult result;
    result.sum = 0.0;
    result.average.reset();
    
    size_t colIndex = sheet.columnIndex(column);
    
    for (size_t i = 0; i < sheet.rowCount(); ++i) {
        const Cell& cell = sheet.cell(i, colIndex);
        
        if (cell.isMissing()) {
            result.count_missing++;
            continue;
        }
        
        auto maybeValue = cell.parseDouble();
        if (!maybeValue) {
            result.count_invalid++;
            continue;
        }
        
        result.count_valid++;
        result.sum += *maybeValue;
    }
    
    if (result.count_valid > 0) {
        result.average = result.sum / static_cast<double>(result.count_valid);
    }
    
    if (report) {
        std::ostringstream oss;
        oss << "Aggregated numeric column '" << column << "': "
            << "valid=" << result.count_valid
            << ", missing=" << result.count_missing
            << ", invalid=" << result.count_invalid;
        if (result.average) {
            oss << ", sum=" << std::fixed << std::setprecision(2) << result.sum
                << ", avg=" << std::fixed << std::setprecision(2) << *result.average;
        } else {
            oss << ", sum=0.00, avg=N/A";
        }
        report->addOperation(oss.str());
        report->rows_read = sheet.rowCount();
        report->invalid_cells = result.count_invalid;
        report->missing_cells = result.count_missing;
    }
    
    return result;
}

} // namespace excel