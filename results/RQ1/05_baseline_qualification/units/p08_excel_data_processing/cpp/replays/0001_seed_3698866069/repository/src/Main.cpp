#include <iostream>
#include <sstream>
#include "ExcelCore.h"
#include "ExcelOps.h"

int main() {
    // Create sample CSV data with headers and some missing/invalid numeric values
    std::istringstream csvInput(R"(Name,Age,Amount
John,25,100.50
Jane,,200.75
Bob,30,invalid
Alice,28,150.25
Charlie,,)");
    
    // Configure CSV import
    excel::CSVConfig config;
    config.delimiter = ',';
    config.quote = '"';
    config.hasHeader = true;
    config.trim = true;
    
    // Import CSV data
    excel::ImportResult importResult = excel::importCSV(csvInput, config, "Demo");
    
    // Create a processing report
    excel::ProcessingReport report;
    
    // Filter rows where Amount > 100.0
    auto predicate = excel::makeNumericGreaterThan("Amount", 100.0, &report);
    excel::Sheet filteredSheet = excel::filterRows(importResult.sheet, predicate, &report);
    
    // Sort by Age (ascending) with missing values last
    excel::SortSpec sortSpec;
    sortSpec.keys.push_back({"Age", true, excel::MissingOrder::Last});
    excel::Sheet sortedSheet = excel::sortRows(filteredSheet, sortSpec, &report);
    
    // Aggregate the Amount column
    excel::AggregationResult aggResult = excel::aggregateNumeric(sortedSheet, "Amount", &report);
    
    // Export to CSV
    std::ostringstream csvOutput;
    excel::exportCSV(sortedSheet, csvOutput, config);
    
    // Print summary and report
    std::cout << "Processed sheet with " << sortedSheet.rowCount() << " rows\n";
    std::cout << "Aggregation result: sum=" << aggResult.sum 
              << ", avg=" << (aggResult.average ? std::to_string(*aggResult.average) : "N/A") << "\n";
    std::cout << "Processing Report:\n" << report.toString();
    std::cout << "Exported CSV:\n" << csvOutput.str();
    
    return 0;
}