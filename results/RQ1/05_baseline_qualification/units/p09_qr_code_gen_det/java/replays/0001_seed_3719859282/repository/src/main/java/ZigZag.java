/**
 * Provides utilities for traversing a matrix in a zigzag (serpentine) pattern.
 */
public class ZigZag {

    /**
     * Performs a two-pass bounded serpentine traversal over unreserved cells only.
     * 
     * First pass counts unreserved cells and allocates the result array.
     * Second pass fills the result with coordinates in zigzag order, skipping reserved cells.
     * 
     * @param size the size of the square matrix
     * @param reserved a boolean matrix indicating which cells are reserved
     * @return a 2D array of coordinates [row, col] in traversal order
     * @throws IllegalArgumentException if reserved is not exactly size x size
     */
    public static int[][] traversal(int size, boolean[][] reserved) {
        // Validate input
        if (reserved == null || reserved.length != size) {
            throw new IllegalArgumentException("Reserved matrix must be exactly size x size");
        }
        for (int i = 0; i < size; i++) {
            if (reserved[i] == null || reserved[i].length != size) {
                throw new IllegalArgumentException("Reserved matrix must be exactly size x size");
            }
        }

        // First pass: count unreserved cells
        int count = 0;
        for (int row = 0; row < size; row++) {
            for (int col = 0; col < size; col++) {
                if (!reserved[row][col]) {
                    count++;
                }
            }
        }

        // Allocate result array with exact count
        int[][] result = new int[count][2];

        // Second pass: fill result with unreserved coordinates in zigzag order
        int index = 0;
        for (int row = 0; row < size; row++) {
            if (row % 2 == 0) {
                // Even rows: left to right
                for (int col = 0; col < size; col++) {
                    if (!reserved[row][col]) {
                        result[index][0] = row;
                        result[index][1] = col;
                        index++;
                    }
                }
            } else {
                // Odd rows: right to left
                for (int col = size - 1; col >= 0; col--) {
                    if (!reserved[row][col]) {
                        result[index][0] = row;
                        result[index][1] = col;
                        index++;
                    }
                }
            }
        }

        return result;
    }
}