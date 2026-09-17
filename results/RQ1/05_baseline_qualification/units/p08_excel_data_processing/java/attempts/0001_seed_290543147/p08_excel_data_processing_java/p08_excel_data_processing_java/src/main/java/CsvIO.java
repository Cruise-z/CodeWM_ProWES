public class CsvIO {
    public static Sheet importCsvFromString(String name, String csv, ProcessingReport report) {
        String[] lines = csv.split("\n");
        
        if (lines.length == 0) {
            return new Sheet(name, new java.util.ArrayList<>(), new java.util.ArrayList<>());
        }
        
        // Parse header
        String[] headerCells = lines[0].split(",", -1);
        java.util.List<String> header = new java.util.ArrayList<>();
        for (String cell : headerCells) {
            header.add(cell.trim());
        }
        
        // Parse rows
        java.util.List<Row> rows = new java.util.ArrayList<>();
        for (int i = 1; i < lines.length; i++) {
            if (lines[i].trim().isEmpty()) {
                continue;
            }
            
            String[] cells = lines[i].split(",", -1);
            java.util.List<Cell> rowCells = new java.util.ArrayList<>();
            
            // Pad with empty cells if needed
            for (int j = 0; j < header.size(); j++) {
                if (j < cells.length) {
                    rowCells.add(Cell.of(cells[j].trim()));
                } else {
                    rowCells.add(Cell.of(""));
                }
            }
            
            rows.add(new Row(header, rowCells));
            report.incrementRowsRead();
        }
        
        return new Sheet(name, header, rows);
    }
    
    public static String toCsvString(Sheet sheet, ProcessingReport report) {
        StringBuilder sb = new StringBuilder();
        
        // Write header
        java.util.List<String> header = sheet.header();
        for (int i = 0; i < header.size(); i++) {
            if (i > 0) {
                sb.append(",");
            }
            sb.append(header.get(i));
        }
        sb.append("\n");
        
        // Write rows
        java.util.List<Row> rows = sheet.rows();
        for (Row row : rows) {
            java.util.List<Cell> cells = row.cells();
            for (int i = 0; i < cells.size(); i++) {
                if (i > 0) {
                    sb.append(",");
                }
                sb.append(cells.get(i).raw());
            }
            sb.append("\n");
            report.incrementRowsWritten();
        }
        
        return sb.toString();
    }
}