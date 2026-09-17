/**
 * Represents the game board for the 2048 game.
 * The board is a 4x4 grid of integers, where each cell can hold a tile value
 * that is a power of two (including 0, which represents an empty cell).
 */
public final class Board {
    private static final int BOARD_SIZE = 4;
    private static final int EMPTY = 0;
    
    private final int[][] grid;

    /**
     * Constructs a new Board with an empty 4x4 grid.
     */
    public Board() {
        this.grid = new int[BOARD_SIZE][BOARD_SIZE];
    }

    /**
     * Clears the board by setting all cells to 0 (empty).
     */
    public void clear() {
        for (int i = 0; i < BOARD_SIZE; i++) {
            for (int j = 0; j < BOARD_SIZE; j++) {
                grid[i][j] = EMPTY;
            }
        }
    }

    /**
     * Returns a deep copy of the board's grid.
     * The caller can modify the returned array without affecting the board.
     *
     * @return a new 4x4 array representing the board's current state
     */
    public int[][] getGridCopy() {
        int[][] copy = new int[BOARD_SIZE][BOARD_SIZE];
        for (int i = 0; i < BOARD_SIZE; i++) {
            System.arraycopy(grid[i], 0, copy[i], 0, BOARD_SIZE);
        }
        return copy;
    }

    /**
     * Sets the value of a cell at the specified position.
     * Validates that the row and column indices are within bounds (0-3),
     * and that the value is either 0 or a positive power of two.
     *
     * @param row   the row index (0-3)
     * @param col   the column index (0-3)
     * @param value the tile value (0 or positive power of two)
     * @throws IllegalArgumentException if indices are out of bounds or value is invalid
     */
    public void setCell(int row, int col, int value) {
        if (row < 0 || row >= BOARD_SIZE) {
            throw new IllegalArgumentException("Row must be between 0 and " + (BOARD_SIZE - 1));
        }
        if (col < 0 || col >= BOARD_SIZE) {
            throw new IllegalArgumentException("Column must be between 0 and " + (BOARD_SIZE - 1));
        }
        if (value != EMPTY && (value <= 0 || (value & (value - 1)) != 0)) {
            throw new IllegalArgumentException("Value must be 0 or a positive power of two");
        }
        grid[row][col] = value;
    }

    /**
     * Moves all tiles in the specified direction according to the 2048 game rules.
     * Processes each row or column independently based on the direction:
     * - LEFT: processes rows from left to right
     * - RIGHT: processes rows from right to left
     * - UP: processes columns from top to bottom
     * - DOWN: processes columns from bottom to top
     *
     * For each line, the algorithm:
     * 1. Reads the values in movement order
     * 2. Compacts non-zero values to the front while maintaining order
     * 3. Merges adjacent equal values once per pair, adding the merged value to score
     * 4. Compacts again and fills remaining positions with zeros
     * 5. Writes back the resulting four values to the grid
     *
     * @param dir the direction to move the tiles
     * @return a MoveResult indicating whether anything changed and how much score was gained
     */
    public MoveResult move(Direction dir) {
        boolean changed = false;
        int scoreGained = 0;
        
        // Process each row or column depending on direction
        switch (dir) {
            case LEFT:
                for (int row = 0; row < BOARD_SIZE; row++) {
                    int[] line = new int[BOARD_SIZE];
                    for (int col = 0; col < BOARD_SIZE; col++) {
                        line[col] = grid[row][col];
                    }
                    MoveResult result = processLine(line);
                    if (result.changed()) {
                        changed = true;
                        scoreGained += result.scoreGained();
                    }
                    for (int col = 0; col < BOARD_SIZE; col++) {
                        if (grid[row][col] != line[col]) {
                            changed = true;
                        }
                        grid[row][col] = line[col];
                    }
                }
                break;
                
            case RIGHT:
                for (int row = 0; row < BOARD_SIZE; row++) {
                    int[] line = new int[BOARD_SIZE];
                    for (int col = 0; col < BOARD_SIZE; col++) {
                        line[BOARD_SIZE - 1 - col] = grid[row][col];
                    }
                    MoveResult result = processLine(line);
                    if (result.changed()) {
                        changed = true;
                        scoreGained += result.scoreGained();
                    }
                    for (int col = 0; col < BOARD_SIZE; col++) {
                        if (grid[row][BOARD_SIZE - 1 - col] != line[col]) {
                            changed = true;
                        }
                        grid[row][col] = line[col];
                    }
                }
                break;
                
            case UP:
                for (int col = 0; col < BOARD_SIZE; col++) {
                    int[] line = new int[BOARD_SIZE];
                    for (int row = 0; row < BOARD_SIZE; row++) {
                        line[row] = grid[row][col];
                    }
                    MoveResult result = processLine(line);
                    if (result.changed()) {
                        changed = true;
                        scoreGained += result.scoreGained();
                    }
                    for (int row = 0; row < BOARD_SIZE; row++) {
                        if (grid[row][col] != line[row]) {
                            changed = true;
                        }
                        grid[row][col] = line[row];
                    }
                }
                break;
                
            case DOWN:
                for (int col = 0; col < BOARD_SIZE; col++) {
                    int[] line = new int[BOARD_SIZE];
                    for (int row = 0; row < BOARD_SIZE; row++) {
                        line[BOARD_SIZE - 1 - row] = grid[row][col];
                    }
                    MoveResult result = processLine(line);
                    if (result.changed()) {
                        changed = true;
                        scoreGained += result.scoreGained();
                    }
                    for (int row = 0; row < BOARD_SIZE; row++) {
                        if (grid[BOARD_SIZE - 1 - row][col] != line[row]) {
                            changed = true;
                        }
                        grid[row][col] = line[row];
                    }
                }
                break;
        }
        
        return new MoveResult(changed, scoreGained);
    }

    /**
     * Processes a single line (array of 4 integers) according to the 2048 merge rules.
     * 
     * @param line an array of 4 integers representing a row or column
     * @return a MoveResult indicating whether the line changed and how much score was gained
     */
    private MoveResult processLine(int[] line) {
        // First pass: compact nonzeros to the left
        int writeIndex = 0;
        for (int readIndex = 0; readIndex < BOARD_SIZE; readIndex++) {
            if (line[readIndex] != EMPTY) {
                line[writeIndex++] = line[readIndex];
            }
        }
        // Fill the rest with zeros
        while (writeIndex < BOARD_SIZE) {
            line[writeIndex++] = EMPTY;
        }
        
        // Second pass: merge adjacent equal numbers
        int scoreGained = 0;
        boolean changed = false;
        for (int i = 0; i < BOARD_SIZE - 1; i++) {
            if (line[i] != EMPTY && line[i] == line[i + 1]) {
                line[i] *= 2;
                scoreGained += line[i];
                line[i + 1] = EMPTY;
                changed = true;
                // Skip the next element since we just merged it
                i++;
            }
        }
        
        // Third pass: compact again to remove the gaps left by merging
        writeIndex = 0;
        for (int readIndex = 0; readIndex < BOARD_SIZE; readIndex++) {
            if (line[readIndex] != EMPTY) {
                line[writeIndex++] = line[readIndex];
            }
        }
        // Fill the rest with zeros
        while (writeIndex < BOARD_SIZE) {
            line[writeIndex++] = EMPTY;
        }
        
        // Check if anything actually changed
        for (int i = 0; i < BOARD_SIZE; i++) {
            if (line[i] != line[i]) {
                changed = true;
                break;
            }
        }
        
        return new MoveResult(changed, scoreGained);
    }

    /**
     * Checks if there is at least one tile with the specified value or greater.
     *
     * @param value the minimum value to check for
     * @return true if any tile has a value >= value, false otherwise
     */
    public boolean hasTileAtLeast(int value) {
        for (int i = 0; i < BOARD_SIZE; i++) {
            for (int j = 0; j < BOARD_SIZE; j++) {
                if (grid[i][j] >= value) {
                    return true;
                }
            }
        }
        return false;
    }

    /**
     * Checks if there are any possible moves remaining.
     * A move is possible if:
     * 1. There is at least one empty cell (0)
     * 2. There are adjacent equal tiles that can be merged
     *
     * @return true if there are possible moves, false otherwise
     */
    public boolean hasAnyMoves() {
        // Check for empty cells
        for (int i = 0; i < BOARD_SIZE; i++) {
            for (int j = 0; j < BOARD_SIZE; j++) {
                if (grid[i][j] == EMPTY) {
                    return true;
                }
            }
        }
        
        // Check for adjacent equal tiles
        // Horizontal adjacent pairs
        for (int row = 0; row < BOARD_SIZE; row++) {
            for (int col = 0; col < BOARD_SIZE - 1; col++) {
                if (grid[row][col] == grid[row][col + 1]) {
                    return true;
                }
            }
        }
        
        // Vertical adjacent pairs
        for (int row = 0; row < BOARD_SIZE - 1; row++) {
            for (int col = 0; col < BOARD_SIZE; col++) {
                if (grid[row][col] == grid[row + 1][col]) {
                    return true;
                }
            }
        }
        
        return false;
    }
}