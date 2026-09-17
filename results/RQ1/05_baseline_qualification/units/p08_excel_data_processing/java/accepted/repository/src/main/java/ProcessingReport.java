import java.util.LinkedHashMap;
import java.util.Map;

public class ProcessingReport {
    private int rowsRead;
    private int rowsKept;
    private int rowsWritten;
    private final LinkedHashMap<String, Integer> invalidCounts;

    public ProcessingReport() {
        this.rowsRead = 0;
        this.rowsKept = 0;
        this.rowsWritten = 0;
        this.invalidCounts = new LinkedHashMap<>();
    }

    public void incrementRowsRead() {
        this.rowsRead++;
    }

    public void incrementRowsKept() {
        this.rowsKept++;
    }

    public void incrementRowsWritten() {
        this.rowsWritten++;
    }

    public void recordInvalid(String column) {
        invalidCounts.put(column, invalidCounts.getOrDefault(column, 0) + 1);
    }

    public int getRowsRead() {
        return this.rowsRead;
    }

    public int getRowsKept() {
        return this.rowsKept;
    }

    public int getRowsWritten() {
        return this.rowsWritten;
    }

    public LinkedHashMap<String, Integer> invalidCounts() {
        return new LinkedHashMap<>(invalidCounts);
    }
}