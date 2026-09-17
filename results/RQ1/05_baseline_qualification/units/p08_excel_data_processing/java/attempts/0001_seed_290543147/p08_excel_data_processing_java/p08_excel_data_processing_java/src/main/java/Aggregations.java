public class Aggregations {
    public static int count(Sheet sheet) {
        return sheet.rows().size();
    }

    public static double sum(Sheet sheet, String column, ProcessingReport report) {
        double total = 0.0;
        for (Row row : sheet.rows()) {
            Double value = ValueParser.toDouble(row.get(column).raw(), column, report);
            if (value != null) {
                total += value;
            }
        }
        return total;
    }

    public static double average(Sheet sheet, String column, ProcessingReport report) {
        double sum = sum(sheet, column, report);
        int count = count(sheet);
        if (count == 0) {
            return 0.0;
        }
        return sum / count;
    }

    public static Double min(Sheet sheet, String column, ProcessingReport report) {
        Double minValue = null;
        for (Row row : sheet.rows()) {
            Double value = ValueParser.toDouble(row.get(column).raw(), column, report);
            if (value != null) {
                if (minValue == null || value < minValue) {
                    minValue = value;
                }
            }
        }
        return minValue;
    }

    public static Double max(Sheet sheet, String column, ProcessingReport report) {
        Double maxValue = null;
        for (Row row : sheet.rows()) {
            Double value = ValueParser.toDouble(row.get(column).raw(), column, report);
            if (value != null) {
                if (maxValue == null || value > maxValue) {
                    maxValue = value;
                }
            }
        }
        return maxValue;
    }
}