/**
 * Represents the game board as a square grid.
 * The board stores player tokens with null representing empty cells.
 */
public final class Board {
    private final int size;
    private final Player[][] grid;

    /**
     * Creates a new Board with the specified size.
     *
     * @param size the size of the square board (must be >= 5)
     * @throws IllegalArgumentException if size < 5
     */
    public Board(int size) {
        if (size < 5) {
            throw new IllegalArgumentException("Board size must be at least 5");
        }
        this.size = size;
        this.grid = new Player[size][size];
    }

    /**
     * Returns the size of the board.
     *
     * @return the board size
     */
    public int getSize() {
        return size;
    }

    /**
     * Checks if the given coordinates are within the board boundaries.
     *
     * @param row the row coordinate
     * @param col the column coordinate
     * @return true if the coordinates are valid, false otherwise
     */
    public boolean isInBounds(int row, int col) {
        return row >= 0 && row < size && col >= 0 && col < size;
    }

    /**
     * Gets the player at the specified position.
     *
     * @param row the row coordinate
     * @param col the column coordinate
     * @return the player at the position, or null if empty
     * @throws IllegalArgumentException if coordinates are out of bounds
     */
    public Player getCell(int row, int col) {
        if (!isInBounds(row, col)) {
            throw new IllegalArgumentException("Coordinates out of bounds");
        }
        return grid[row][col];
    }

    /**
     * Checks if the cell at the specified position is empty.
     *
     * @param row the row coordinate
     * @param col the column coordinate
     * @return true if the cell is empty, false otherwise
     * @throws IllegalArgumentException if coordinates are out of bounds
     */
    public boolean isEmpty(int row, int col) {
        if (!isInBounds(row, col)) {
            throw new IllegalArgumentException("Coordinates out of bounds");
        }
        return grid[row][col] == null;
    }

    /**
     * Sets the cell at the specified position to the given player.
     * The operation only succeeds if the cell is empty and coordinates are valid.
     *
     * @param row the row coordinate
     * @param col the column coordinate
     * @param player the player to set
     * @return true if the cell was successfully set, false otherwise
     * @throws IllegalArgumentException if coordinates are out of bounds
     */
    public boolean setCell(int row, int col, Player player) {
        if (!isInBounds(row, col)) {
            throw new IllegalArgumentException("Coordinates out of bounds");
        }
        if (grid[row][col] != null) {
            return false;
        }
        grid[row][col] = player;
        return true;
    }

    /**
     * Clears the cell at the specified position.
     * The operation only succeeds if the coordinates are valid.
     *
     * @param row the row coordinate
     * @param col the column coordinate
     * @throws IllegalArgumentException if coordinates are out of bounds
     */
    public void clearCell(int row, int col) {
        if (!isInBounds(row, col)) {
            throw new IllegalArgumentException("Coordinates out of bounds");
        }
        grid[row][col] = null;
    }

    /**
     * Returns a defensive copy of the board's current state.
     * Each element in the returned array is a reference to the corresponding
     * player on the board (null for empty).
     *
     * @return a 2D array representing the board state
     */
    public Player[][] snapshot() {
        Player[][] snapshot = new Player[size][size];
        for (int i = 0; i < size; i++) {
            System.arraycopy(grid[i], 0, snapshot[i], 0, size);
        }
        return snapshot;
    }
}