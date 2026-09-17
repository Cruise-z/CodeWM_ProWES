#include <cassert>
#include <sstream>
#include "ExcelCore.h"
#include "ExcelOps.h"

int main() {
    // Test 1: Runtime wiring smoke test
    {
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
        excel::ImportResult importResult = excel::importCSV(csvInput, config, "Test");
        
        // Create a processing report
        excel::ProcessingReport report;
        
        // Filter rows where Amount > 100.0
        auto predicate = excel::makeNumericGreaterThan("Amount", 100.0, &report);
        excel::Sheet filteredSheet = excel::filterRows(importResult.sheet, predicate, &report);
        
        // Verify filtered sheet has correct row count
        assert(filteredSheet.rowCount() == 3); // John, Jane, Alice should be kept
        
        // Sort by Age (ascending) with missing values last
        excel::SortSpec sortSpec;
        sortSpec.keys.push_back({"Age", true, excel::MissingOrder::Last});
        excel::Sheet sortedSheet = excel::sortRows(filteredSheet, sortSpec, &report);
        
        // Verify sorted sheet has correct row count
        assert(sortedSheet.rowCount() == 3);
        
        // Check that rows are in expected order (Jane with missing age comes last)
        // Row 0: John (age 25)
        // Row 1: Alice (age 28)  
        // Row 2: Jane (age missing)
        const excel::Cell& firstCell = sortedSheet.cell(0, 1); // Age column of first row
        assert(firstCell.parseInt().value_or(0) == 25);
        
        const excel::Cell& thirdCell = sortedSheet.cell(2, 1); // Age column of third row
        assert(thirdCell.isMissing()); // Jane's age is missing
        
        // Aggregate the Amount column
        excel::AggregationResult aggResult = excel::aggregateNumeric(sortedSheet, "Amount", &report);
        
        // Verify aggregation results
        assert(aggResult.count_valid == 3);
        assert(aggResult.count_missing == 1); // Jane's amount is missing (but not counted as missing since filtering removed her)
        assert(aggResult.count_invalid == 1); // Bob's amount is invalid
        assert(aggResult.sum == 451.50); // 100.50 + 200.75 + 150.25
        assert(aggResult.average.has_value());
        assert(*aggResult.average == 150.50); // 451.50 / 3
        
        // Export to CSV
        std::ostringstream csvOutput;
        excel::exportCSV(sortedSheet, csvOutput, config);
        
        // Verify exported CSV contains expected header and row order
        std::string outputStr = csvOutput.str();
        assert(outputStr.find("Name,Age,Amount") != std::string::npos);
        assert(outputStr.find("John,25,100.50") != std::string::npos);
        assert(outputStr.find("Alice,28,150.25") != std::string::npos);
    }
    
    // Test 2: Core rule with missing/invalid
    {
        // Create CSV with missing and invalid values
        std::istringstream csvInput(R"(Name,Score
Alice,
Bob,invalid
Charlie,85
David,92
Eve,)");
        
        excel::CSVConfig config;
        config.hasHeader = true;
        
        excel::ImportResult importResult = excel::importCSV(csvInput, config, "Test2");
        
        excel::ProcessingReport report;
        
        // Test filter predicate treats missing as false
        auto predicate = excel::makeNumericGreaterThan("Score", 80.0, &report);
        excel::Sheet filteredSheet = excel::filterRows(importResult.sheet, predicate, &report);
        
        // Should keep Charlie and David (scores 85 and 92)
        assert(filteredSheet.rowCount() == 2);
        
        // Verify counts in report
        assert(report.missing_cells == 2); // Alice and Eve have missing scores
        assert(report.invalid_cells == 1); // Bob has invalid score
        
        // Test aggregation ignores missing/invalid
        excel::AggregationResult aggResult = excel::aggregateNumeric(importResult.sheet, "Score", &report);
        
        // Should have 2 valid (Charlie and David), 2 missing, 1 invalid
        assert(aggResult.count_valid == 2);
        assert(aggResult.count_missing == 2);
        assert(aggResult.count_invalid == 1);
        assert(aggResult.sum == 177.0); // 85 + 92
        assert(aggResult.average.has_value());
        assert(*aggResult.average == 88.5); // 177 / 2
        
        // Test ProcessingReport toString() contains deterministic counts
        std::string reportStr = report.toString();
        assert(reportStr.find("Rows read: 5") != std::string::npos);
        assert(reportStr.find("Invalid cells: 1") != std::string::npos);
        assert(reportStr.find("Missing cells: 2") != std::string::npos);
    }
    
    return 0;
}