import java.util.Comparator;
import java.util.List;

public class Sorters {
    public static class Order {
        private final String column;
        private final boolean ascending;

        public Order(String column, boolean ascending) {
            this.column = column;
            this.ascending = ascending;
        }

        public String column() {
            return this.column;
        }

        public boolean ascending() {
            return this.ascending;
        }
    }

    public static Comparator<Row> comparator(List<Order> orders) {
        return (row1, row2) -> {
            for (Order order : orders) {
                String column = order.column();
                boolean ascending = order.ascending();
                
                Cell cell1 = row1.get(column);
                Cell cell2 = row2.get(column);
                
                String raw1 = cell1.raw();
                String raw2 = cell2.raw();
                
                // Determine if cells are blank
                boolean blank1 = cell1.isBlank();
                boolean blank2 = cell2.isBlank();
                
                // Handle blank values - they should be ordered last regardless of sort direction
                if (blank1 && blank2) {
                    // Both blank, maintain relative order (stable sort)
                    continue;
                } else if (blank1) {
                    // Only first is blank, put it last
                    return ascending ? 1 : -1;
                } else if (blank2) {
                    // Only second is blank, put it last
                    return ascending ? -1 : 1;
                }
                
                // Compare non-blank values
                int comparison = raw1.compareTo(raw2);
                if (comparison != 0) {
                    return ascending ? comparison : -comparison;
                }
            }
            
            // All compared values were equal, maintain original order (stable sort)
            return 0;
        };
    }
}