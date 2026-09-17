/**
 * Immutable class representing a tile spawn position and value.
 * Contains row, column, and value information for a tile to be placed on the board.
 */
public final class Spawn {
    private final int row;
    private final int col;
    private final int value;

    /**
     * Constructs a new Spawn with the specified position and value.
     *
     * @param row   the row index (0-3) where the tile should be placed
     * @param col   the column index (0-3) where the tile should be placed
     * @param value the tile value (must be a positive power of two)
     * @throws IllegalArgumentException if row or col are out of bounds (0-3)
     *                                  or if value is not a positive power of two
     */
    public Spawn(int row, int col, int value) {
        if (row < 0 || row > 3) {
            throw new IllegalArgumentException("Row must be between 0 and 3 inclusive");
        }
        if (col < 0 || col > 3) {
            throw new IllegalArgumentException("Column must be between 0 and 3 inclusive");
        }
        if (value <= 0 || (value & (value - 1)) != 0) {
            throw new IllegalArgumentException("Value must be a positive power of two");
        }
        
        this.row = row;
        this.col = col;
        this.value = value;
    }

    /**
     * Returns the row index where the tile should be placed.
     *
     * @return the row index (0-3)
     */
    public int row() {
        return row;
    }

    /**
     * Returns the column index where the tile should be placed.
     *
     * @return the column index (0-3)
     */
    public int col() {
        return col;
    }

    /**
     * Returns the tile value to be placed.
     *
     * @return the tile value (positive power of two)
     */
    public int value() {
        return value;
    }
}