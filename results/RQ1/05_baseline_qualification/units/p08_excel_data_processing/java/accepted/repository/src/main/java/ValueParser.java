public class ValueParser {
    public static Double toDouble(String raw, String column, ProcessingReport report) {
        if (raw == null || raw.trim().isEmpty()) {
            return null;
        }
        
        try {
            return Double.valueOf(raw.trim());
        } catch (NumberFormatException e) {
            report.recordInvalid(column);
            return null;
        }
    }
}