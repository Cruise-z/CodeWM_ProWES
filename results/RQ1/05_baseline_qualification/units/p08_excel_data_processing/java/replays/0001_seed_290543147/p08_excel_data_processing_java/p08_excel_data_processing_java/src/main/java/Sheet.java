import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.function.Predicate;

public class Sheet {
    private final String name;
    private final List<String> header;
    private final List<Row> rows;

    public Sheet(String name, List<String> header, List<Row> rows) {
        this.name = name;
        this.header = new ArrayList<>(header);
        this.rows = new ArrayList<>(rows);
    }

    public String name() {
        return this.name;
    }

    public List<String> header() {
        return new ArrayList<>(this.header);
    }

    public List<Row> rows() {
        return new ArrayList<>(this.rows);
    }

    public Sheet filter(Predicate<Row> predicate, ProcessingReport report) {
        List<Row> filteredRows = new ArrayList<>();
        for (Row row : this.rows) {
            if (predicate.test(row)) {
                filteredRows.add(row);
                report.incrementRowsKept();
            }
        }
        return new Sheet(this.name, this.header, filteredRows);
    }

    public Sheet sort(List<Sorters.Order> orders) {
        List<Row> sortedRows = new ArrayList<>(this.rows);
        sortedRows.sort(Sorters.comparator(orders));
        return new Sheet(this.name, this.header, sortedRows);
    }
}