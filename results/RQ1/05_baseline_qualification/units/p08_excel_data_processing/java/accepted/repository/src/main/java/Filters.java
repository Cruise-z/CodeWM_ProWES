import java.util.function.Predicate;

public class Filters {
    public static Predicate<Row> equals(String column, String value) {
        return row -> {
            Cell cell = row.get(column);
            return value.equals(cell.raw());
        };
    }

    public static Predicate<Row> contains(String column, String fragment) {
        return row -> {
            Cell cell = row.get(column);
            return cell.raw().contains(fragment);
        };
    }

    public static Predicate<Row> numericGreaterThan(String column, double threshold, ProcessingReport report) {
        return row -> {
            Double value = ValueParser.toDouble(row.get(column).raw(), column, report);
            return value != null && value > threshold;
        };
    }
}