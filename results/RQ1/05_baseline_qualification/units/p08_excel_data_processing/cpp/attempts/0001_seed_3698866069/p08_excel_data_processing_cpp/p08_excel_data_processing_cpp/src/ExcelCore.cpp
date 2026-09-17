#include "ExcelCore.h"
#include <sstream>
#include <algorithm>
#include <cctype>
#include <iomanip>

namespace excel {

// Cell implementation
Cell::Cell() : raw_() {}

Cell::Cell(const std::string& raw) : raw_(raw) {}

bool Cell::isMissing() const {
    if (raw_.empty()) {
        return true;
    }
    // Check if string contains only whitespace
    return std::all_of(raw_.begin(), raw_.end(), ::isspace);
}

const std::string& Cell::asString() const {
    return raw_;
}

std::optional<long long> Cell::parseInt() const {
    if (isMissing()) {
        return std::nullopt;
    }
    
    try {
        size_t pos;
        // Trim whitespace
        std::string trimmed = raw_;
        trimmed.erase(trimmed.begin(), std::find_if(trimmed.begin(), trimmed.end(), [](unsigned char ch) {
            return !std::isspace(ch);
        }));
        trimmed.erase(std::find_if(trimmed.rbegin(), trimmed.rend(), [](unsigned char ch) {
            return !std::isspace(ch);
        }).base(), trimmed.end());
        
        long long result = std::stoll(trimmed, &pos);
        // Ensure we consumed the entire string
        if (pos == trimmed.length()) {
            return result;
        }
    } catch (const std::exception&) {
        // Parsing failed, return nullopt
    }
    return std::nullopt;
}

std::optional<double> Cell::parseDouble() const {
    if (isMissing()) {
        return std::nullopt;
    }
    
    try {
        size_t pos;
        // Trim whitespace
        std::string trimmed = raw_;
        trimmed.erase(trimmed.begin(), std::find_if(trimmed.begin(), trimmed.end(), [](unsigned char ch) {
            return !std::isspace(ch);
        }));
        trimmed.erase(std::find_if(trimmed.rbegin(), trimmed.rend(), [](unsigned char ch) {
            return !std::isspace(ch);
        }).base(), trimmed.end());
        
        double result = std::stod(trimmed, &pos);
        // Ensure we consumed the entire string
        if (pos == trimmed.length()) {
            return result;
        }
    } catch (const std::exception&) {
        // Parsing failed, return nullopt
    }
    return std::nullopt;
}

// Sheet implementation
Sheet::Sheet() : name_(""), headers_(), nameToIndex_(), rows_() {}

Sheet::Sheet(const std::string& name, const std::vector<std::string>& headers)
    : name_(name), headers_(headers), nameToIndex_(), rows_() {
    // Build column name -> index mapping
    for (size_t i = 0; i < headers_.size(); ++i) {
        nameToIndex_[headers_[i]] = i;
    }
}

const std::string& Sheet::getName() const {
    return name_;
}

const std::vector<std::string>& Sheet::getHeaders() const {
    return headers_;
}

bool Sheet::hasColumn(const std::string& columnName) const {
    return nameToIndex_.find(columnName) != nameToIndex_.end();
}

size_t Sheet::columnIndex(const std::string& columnName) const {
    auto it = nameToIndex_.find(columnName);
    if (it == nameToIndex_.end()) {
        throw std::out_of_range("Column not found: " + columnName);
    }
    return it->second;
}

void Sheet::appendRow(const std::vector<std::string>& values) {
    if (values.size() != headers_.size()) {
        throw std::invalid_argument(
            "Number of values (" + std::to_string(values.size()) +
            ") does not match number of columns (" + std::to_string(headers_.size()) + ")"
        );
    }
    
    rows_.push_back({});
    auto& newRow = rows_.back();
    newRow.reserve(values.size());
    
    for (const auto& value : values) {
        newRow.emplace_back(value);
    }
}

size_t Sheet::rowCount() const {
    return rows_.size();
}

size_t Sheet::columnCount() const {
    return headers_.size();
}

const Cell& Sheet::cell(size_t row, size_t col) const {
    if (row >= rows_.size() || col >= headers_.size()) {
        throw std::out_of_range("Cell index out of range");
    }
    return rows_[row][col];
}

Sheet Sheet::cloneWithSubsetColumns(const std::vector<size_t>& indices) const {
    // Validate indices
    for (size_t idx : indices) {
        if (idx >= headers_.size()) {
            throw std::out_of_range("Column index out of range");
        }
    }
    
    // Create new headers
    std::vector<std::string> newHeaders;
    newHeaders.reserve(indices.size());
    for (size_t idx : indices) {
        newHeaders.push_back(headers_[idx]);
    }
    
    // Create new sheet
    Sheet newSheet(name_, newHeaders);
    
    // Copy rows
    for (const auto& row : rows_) {
        std::vector<std::string> newRow;
        newRow.reserve(indices.size());
        for (size_t idx : indices) {
            newRow.push_back(row[idx].asString());
        }
        newSheet.appendRow(newRow);
    }
    
    return newSheet;
}

// Workbook implementation
void Workbook::addSheet(const Sheet& sheet) {
    std::string name = sheet.getName();
    if (nameToIndex_.find(name) != nameToIndex_.end()) {
        throw std::invalid_argument("Sheet with name '" + name + "' already exists");
    }
    
    sheets_.push_back(sheet);
    nameToIndex_[name] = sheets_.size() - 1;
}

size_t Workbook::sheetCount() const {
    return sheets_.size();
}

const Sheet& Workbook::getSheetByIndex(size_t index) const {
    if (index >= sheets_.size()) {
        throw std::out_of_range("Sheet index out of range");
    }
    return sheets_[index];
}

const Sheet& Workbook::getSheetByName(const std::string& name) const {
    auto it = nameToIndex_.find(name);
    if (it == nameToIndex_.end()) {
        throw std::out_of_range("Sheet not found: " + name);
    }
    return sheets_[it->second];
}

// CSV parsing implementation
ImportResult importCSV(std::istream& input, const CSVConfig& config, const std::string& sheetName) {
    ImportResult result;
    result.sheet = Sheet(sheetName, {});
    result.rowsRead = 0;
    result.missingCells = 0;
    
    std::string line;
    std::vector<std::string> headers;
    bool firstLine = true;
    
    while (std::getline(input, line)) {
        // Remove trailing carriage return
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        
        if (line.empty()) {
            continue;
        }
        
        // Parse line into fields
        std::vector<std::string> fields;
        std::string field;
        bool inQuotes = false;
        char prevChar = 0;
        
        for (size_t i = 0; i < line.length(); ++i) {
            char c = line[i];
            
            if (c == config.quote) {
                if (inQuotes && prevChar == config.quote) {
                    // Escaped quote
                    field += c;
                    prevChar = c;
                    continue;
                } else if (!inQuotes && !field.empty()) {
                    // Quote inside field - not allowed unless it's an escaped quote
                    // But we'll treat this as a regular character for simplicity
                }
                
                inQuotes = !inQuotes;
                prevChar = c;
                continue;
            }
            
            if (c == config.delimiter && !inQuotes) {
                // End of field
                if (config.trim) {
                    // Trim the field
                    size_t start = field.find_first_not_of(" \t");
                    if (start == std::string::npos) {
                        field.clear();
                    } else {
                        size_t end = field.find_last_not_of(" \t");
                        field = field.substr(start, end - start + 1);
                    }
                }
                
                fields.push_back(field);
                field.clear();
                prevChar = c;
                continue;
            }
            
            field += c;
            prevChar = c;
        }
        
        // Handle last field
        if (inQuotes) {
            // Unclosed quote - treat as regular content
            fields.push_back(field);
        } else {
            if (config.trim) {
                // Trim the field
                size_t start = field.find_first_not_of(" \t");
                if (start == std::string::npos) {
                    field.clear();
                } else {
                    size_t end = field.find_last_not_of(" \t");
                    field = field.substr(start, end - start + 1);
                }
            }
            fields.push_back(field);
        }
        
        if (firstLine && config.hasHeader) {
            // This is the header line
            headers = fields;
            result.sheet = Sheet(sheetName, headers);
            firstLine = false;
            continue;
        }
        
        // Add row to sheet
        if (!firstLine) {
            // If we have headers, verify the number of fields matches
            if (headers.empty()) {
                // Synthesize column names
                headers.resize(fields.size());
                for (size_t i = 0; i < fields.size(); ++i) {
                    headers[i] = "C" + std::to_string(i+1);
                }
                result.sheet = Sheet(sheetName, headers);
            }
            
            try {
                result.sheet.appendRow(fields);
                result.rowsRead++;
                
                // Count missing cells
                for (const auto& f : fields) {
                    if (f.empty()) {
                        result.missingCells++;
                    }
                }
            } catch (const std::exception&) {
                // Skip invalid rows
                continue;
            }
        }
    }
    
    return result;
}

// CSV export implementation
void exportCSV(const Sheet& sheet, std::ostream& output, const CSVConfig& config) {
    const std::vector<std::string>& headers = sheet.getHeaders();
    
    // Write headers if they exist
    if (!headers.empty()) {
        bool first = true;
        for (const auto& header : headers) {
            if (!first) {
                output << config.delimiter;
            }
            
            // Check if we need to quote this header
            bool needsQuote = header.empty() || 
                             header.find(config.delimiter) != std::string::npos ||
                             header.find(config.quote) != std::string::npos ||
                             header.find('\n') != std::string::npos ||
                             header.find('\r') != std::string::npos ||
                             header.front() == ' ' || 
                             header.back() == ' ';
            
            if (needsQuote) {
                output << config.quote;
                // Escape quotes in the header
                std::string escaped = header;
                size_t pos = 0;
                while ((pos = escaped.find(config.quote, pos)) != std::string::npos) {
                    escaped.insert(pos, 1, config.quote);
                    pos += 2; // Move past the escaped quote
                }
                output << escaped;
                output << config.quote;
            } else {
                output << header;
            }
            first = false;
        }
        output << "\n";
    }
    
    // Write data rows
    for (size_t i = 0; i < sheet.rowCount(); ++i) {
        bool first = true;
        for (size_t j = 0; j < sheet.columnCount(); ++j) {
            if (!first) {
                output << config.delimiter;
            }
            
            const Cell& cell = sheet.cell(i, j);
            std::string value = cell.asString();
            
            // Check if we need to quote this field
            bool needsQuote = value.empty() || 
                             value.find(config.delimiter) != std::string::npos ||
                             value.find(config.quote) != std::string::npos ||
                             value.find('\n') != std::string::npos ||
                             value.find('\r') != std::string::npos ||
                             value.front() == ' ' || 
                             value.back() == ' ';
            
            if (needsQuote) {
                output << config.quote;
                // Escape quotes in the value
                std::string escaped = value;
                size_t pos = 0;
                while ((pos = escaped.find(config.quote, pos)) != std::string::npos) {
                    escaped.insert(pos, 1, config.quote);
                    pos += 2; // Move past the escaped quote
                }
                output << escaped;
                output << config.quote;
            } else {
                output << value;
            }
            first = false;
        }
        output << "\n";
    }
}

} // namespace excel