#ifndef EXCEL_CORE_H
#define EXCEL_CORE_H

#include <string>
#include <vector>
#include <unordered_map>
#include <functional>
#include <istream>
#include <ostream>
#include <optional>
#include <stdexcept>

namespace excel {

/**
 * Represents a cell in a spreadsheet with raw string content.
 */
class Cell {
private:
    std::string raw_;

public:
    /**
     * Constructs an empty cell.
     */
    Cell();

    /**
     * Constructs a cell with the given raw string content.
     * @param raw The raw string content of the cell.
     */
    explicit Cell(const std::string& raw);

    /**
     * Checks if the cell is considered missing (empty or only whitespace).
     * @return true if the cell is missing, false otherwise.
     */
    bool isMissing() const;

    /**
     * Gets the raw string content of the cell.
     * @return A constant reference to the raw string content.
     */
    const std::string& asString() const;

    /**
     * Attempts to parse the cell's content as an integer.
     * @return An optional containing the parsed integer if successful, or std::nullopt if not.
     */
    std::optional<long long> parseInt() const;

    /**
     * Attempts to parse the cell's content as a double.
     * @return An optional containing the parsed double if successful, or std::nullopt if not.
     */
    std::optional<double> parseDouble() const;
};

/**
 * Represents a sheet in a workbook with named columns and rows of cells.
 */
class Sheet {
private:
    std::string name_;
    std::vector<std::string> headers_;
    std::unordered_map<std::string, size_t> nameToIndex_;
    std::vector<std::vector<Cell>> rows_;

public:
    /**
     * Constructs an empty sheet with no name and no headers.
     */
    Sheet();

    /**
     * Constructs a sheet with a given name and headers.
     * @param name The name of the sheet.
     * @param headers The column headers.
     */
    Sheet(const std::string& name, const std::vector<std::string>& headers);

    /**
     * Gets the name of the sheet.
     * @return A constant reference to the sheet name.
     */
    const std::string& getName() const;

    /**
     * Gets the column headers of the sheet.
     * @return A constant reference to the vector of column headers.
     */
    const std::vector<std::string>& getHeaders() const;

    /**
     * Checks if a column with the given name exists.
     * @param columnName The name of the column to look for.
     * @return true if the column exists, false otherwise.
     */
    bool hasColumn(const std::string& columnName) const;

    /**
     * Gets the index of a column by its name.
     * @param columnName The name of the column.
     * @return The index of the column.
     * @throws std::out_of_range if the column does not exist.
     */
    size_t columnIndex(const std::string& columnName) const;

    /**
     * Appends a new row to the sheet.
     * @param values The values to append as a new row.
     * @throws std::invalid_argument if the number of values doesn't match the number of columns.
     */
    void appendRow(const std::vector<std::string>& values);

    /**
     * Gets the number of rows in the sheet, including the header row.
     * @return The number of rows.
     */
    size_t rowCount() const;

    /**
     * Gets the number of columns in the sheet.
     * @return The number of columns.
     */
    size_t columnCount() const;

    /**
     * Gets a reference to a cell in the sheet.
     * @param row The row index (0-based).
     * @param col The column index (0-based).
     * @return A constant reference to the cell.
     * @throws std::out_of_range if the indices are out of bounds.
     */
    const Cell& cell(size_t row, size_t col) const;

    /**
     * Creates a new sheet with only the specified columns.
     * @param indices The indices of the columns to keep.
     * @return A new sheet containing only the specified columns.
     */
    Sheet cloneWithSubsetColumns(const std::vector<size_t>& indices) const;
};

/**
 * Represents a workbook containing multiple sheets.
 */
class Workbook {
private:
    std::vector<Sheet> sheets_;
    std::unordered_map<std::string, size_t> nameToIndex_;

public:
    /**
     * Adds a sheet to the workbook.
     * @param sheet The sheet to add.
     */
    void addSheet(const Sheet& sheet);

    /**
     * Gets the number of sheets in the workbook.
     * @return The number of sheets.
     */
    size_t sheetCount() const;

    /**
     * Gets a sheet by its index.
     * @param index The index of the sheet.
     * @return A constant reference to the sheet.
     * @throws std::out_of_range if the index is out of bounds.
     */
    const Sheet& getSheetByIndex(size_t index) const;

    /**
     * Gets a sheet by its name.
     * @param name The name of the sheet.
     * @return A constant reference to the sheet.
     * @throws std::out_of_range if the sheet does not exist.
     */
    const Sheet& getSheetByName(const std::string& name) const;
};

/**
 * Configuration for CSV import/export operations.
 */
struct CSVConfig {
    char delimiter = ',';
    char quote = '"';
    bool hasHeader = true;
    bool trim = true;
};

/**
 * Result of importing a CSV file.
 */
struct ImportResult {
    Sheet sheet;
    size_t rowsRead = 0;
    size_t missingCells = 0;
};

/**
 * Imports a CSV file into a Sheet.
 * @param input The input stream to read from.
 * @param config The CSV configuration.
 * @param sheetName The name to assign to the resulting sheet.
 * @return The import result.
 */
ImportResult importCSV(std::istream& input, const CSVConfig& config, const std::string& sheetName);

/**
 * Exports a sheet to a CSV file.
 * @param sheet The sheet to export.
 * @param output The output stream to write to.
 * @param config The CSV configuration.
 */
void exportCSV(const Sheet& sheet, std::ostream& output, const CSVConfig& config);

} // namespace excel

#endif // EXCEL_CORE_H