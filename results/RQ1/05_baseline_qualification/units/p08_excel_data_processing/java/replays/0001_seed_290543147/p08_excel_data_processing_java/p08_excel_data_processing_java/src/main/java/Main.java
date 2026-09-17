public class Main {
    public static void main(String[] args) {
        // Fixed CSV string for demonstration
        String csv = "Name,Country,Sales\n" +
                     "Alice,US,1000\n" +
                     "Bob,CA,1500\n" +
                     "Charlie,US,2000";
        
        // Phase 1: Import with fresh report
        ProcessingReport reportImport = new ProcessingReport();
        Sheet importedSheet = CsvIO.importCsvFromString("SalesData", csv, reportImport);
        
        // Phase 2: Filter Country == US with fresh report
        ProcessingReport reportFilter = new ProcessingReport();
        Sheet filteredSheet = importedSheet.filter(Filters.equals("Country", "US"), reportFilter);
        
        // Phase 3: Sort descending by Name
        Sorters.Order nameDesc = new Sorters.Order("Name", false);
        Sheet sortedSheet = filteredSheet.sort(java.util.Arrays.asList(nameDesc));
        
        // Phase 4: Sum Sales with fresh report
        ProcessingReport reportAggregation = new ProcessingReport();
        double sum = Aggregations.sum(sortedSheet, "Sales", reportAggregation);
        
        // Phase 5: Export with fresh report
        ProcessingReport reportExport = new ProcessingReport();
        String exportedCsv = CsvIO.toCsvString(sortedSheet, reportExport);
        
        // Print concise deterministic summary
        System.out.println("Import: " + reportImport.getRowsRead() + " rows read");
        System.out.println("Filter: " + reportFilter.getRowsKept() + " rows kept");
        System.out.println("Sum: " + sum + " Sales total");
        System.out.println("Export: " + reportExport.getRowsWritten() + " rows written");
    }
}