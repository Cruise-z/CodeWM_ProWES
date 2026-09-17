import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class MainTest {

    @Test
    public void testRuntimeInvocation() {
        // Test that Main.main runs without throwing exceptions
        Main.main(new String[0]);
    }

    @Test
    public void testThreeRowPipeline() {
        // Test the three-row pipeline: import, filter, sort, sum
        String csv = "Name,Country,Sales\n" +
                     "Alice,US,1000\n" +
                     "Bob,CA,1500\n" +
                     "Charlie,US,2000";

        // Import with fresh report
        ProcessingReport reportImport = new ProcessingReport();
        Sheet importedSheet = CsvIO.importCsvFromString("SalesData", csv, reportImport);
        assertEquals(3, reportImport.getRowsRead());

        // Filter Country == US with fresh report
        ProcessingReport reportFilter = new ProcessingReport();
        Sheet filteredSheet = importedSheet.filter(Filters.equals("Country", "US"), reportFilter);
        assertEquals(2, reportFilter.getRowsKept());

        // Sort descending by Name
        Sorters.Order nameDesc = new Sorters.Order("Name", false);
        Sheet sortedSheet = filteredSheet.sort(java.util.Arrays.asList(nameDesc));

        // Verify sorting order
        assertEquals("Charlie", sortedSheet.rows().get(0).get("Name").raw());
        assertEquals("Alice", sortedSheet.rows().get(1).get("Name").raw());

        // Sum Sales with fresh report
        ProcessingReport reportAggregation = new ProcessingReport();
        double sum = Aggregations.sum(sortedSheet, "Sales", reportAggregation);
        assertEquals(3000.0, sum);
        assertTrue(reportAggregation.invalidCounts().isEmpty());
    }

    @Test
    public void testInvalidRoundTrip() {
        // Test invalid data handling and round-trip export/import
        String csv = "Name,Sales\n" +
                     "Alice,1000\n" +
                     "Bob,bad\n" +
                     "Charlie,\n" +
                     "Dana,2000";

        // Sum exactly once with fresh report
        ProcessingReport reportAggregation = new ProcessingReport();
        double sum = Aggregations.sum(CsvIO.importCsvFromString("SalesData", csv, new ProcessingReport()), "Sales", reportAggregation);
        assertEquals(3000.0, sum);
        assertEquals(Integer.valueOf(1), reportAggregation.invalidCounts().get("Sales"));

        // Export with fresh report
        ProcessingReport reportExport = new ProcessingReport();
        String exportedCsv = CsvIO.toCsvString(CsvIO.importCsvFromString("SalesData", csv, new ProcessingReport()), reportExport);
        assertEquals(4, reportExport.getRowsWritten());

        // Re-import with fresh report
        ProcessingReport reportReimport = new ProcessingReport();
        Sheet reimportedSheet = CsvIO.importCsvFromString("SalesData", exportedCsv, reportReimport);
        assertEquals(4, reportReimport.getRowsRead());
        assertEquals(reimportedSheet.header(), CsvIO.importCsvFromString("SalesData", csv, new ProcessingReport()).header());
        assertEquals(4, reimportedSheet.rows().size());
        
        // Verify Bob's Sales remains "bad"
        assertEquals("bad", reimportedSheet.rows().get(1).get("Sales").raw());
    }
}