public class Cell {
    private final String raw;

    private Cell(String raw) {
        this.raw = (raw == null) ? "" : raw;
    }

    public static Cell of(String raw) {
        return new Cell(raw);
    }

    public String raw() {
        return this.raw;
    }

    public boolean isBlank() {
        return this.raw.trim().isEmpty();
    }
}