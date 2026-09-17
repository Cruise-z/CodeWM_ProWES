/**
 * Provides utilities for defining, placing, and verifying finder patterns in QR codes.
 * Finder patterns are 7x7 squares located at three corners of the QR code matrix.
 */
public class FinderPattern {
    
    /**
     * Creates a reserved mask for finder patterns of the given size.
     * The mask indicates which cells are reserved for finder patterns.
     * 
     * @param size the size of the QR code matrix (must be odd and >= 21)
     * @return a boolean matrix where true indicates a reserved cell
     * @throws IllegalArgumentException if size is less than 21 or even
     */
    public static boolean[][] reservedMask(int size) {
        if (size < 21) {
            throw new IllegalArgumentException("Size must be at least 21");
        }
        if (size % 2 == 0) {
            throw new IllegalArgumentException("Size must be odd");
        }
        
        boolean[][] reserved = new boolean[size][size];
        
        // Top-left finder pattern (7x7 square)
        for (int i = 0; i < 7; i++) {
            for (int j = 0; j < 7; j++) {
                reserved[i][j] = true;
            }
        }
        
        // Top-right finder pattern (7x7 square)
        for (int i = 0; i < 7; i++) {
            for (int j = 0; j < 7; j++) {
                reserved[i][size - 7 + j] = true;
            }
        }
        
        // Bottom-left finder pattern (7x7 square)
        for (int i = 0; i < 7; i++) {
            for (int j = 0; j < 7; j++) {
                reserved[size - 7 + i][j] = true;
            }
        }
        
        return reserved;
    }
    
    /**
     * Places the finder patterns on the given QR matrix by setting their cells to true.
     * 
     * @param matrix the QR matrix to modify
     */
    public static void place(QRMatrix matrix) {
        boolean[][] reserved = reservedMask(matrix.getSize());
        int size = matrix.getSize();
        
        // Place the finder patterns
        for (int i = 0; i < 7; i++) {
            for (int j = 0; j < 7; j++) {
                // Top-left
                if (reserved[i][j]) {
                    matrix.set(i, j, true);
                }
                
                // Top-right
                if (reserved[i][size - 7 + j]) {
                    matrix.set(i, size - 7 + j, true);
                }
                
                // Bottom-left
                if (reserved[size - 7 + i][j]) {
                    matrix.set(size - 7 + i, j, true);
                }
            }
        }
    }
    
    /**
     * Verifies that the finder patterns are correctly placed on the given QR matrix.
     * Throws an IllegalArgumentException if any required finder cell is not true
     * or if any reserved cell (that shouldn't be set) is true.
     * 
     * @param matrix the QR matrix to verify
     * @throws IllegalArgumentException if the finder pattern is incorrect
     */
    public static void verify(QRMatrix matrix) {
        boolean[][] reserved = reservedMask(matrix.getSize());
        int size = matrix.getSize();
        
        // Verify that all finder cells are true
        for (int i = 0; i < 7; i++) {
            for (int j = 0; j < 7; j++) {
                // Top-left
                if (reserved[i][j] && !matrix.get(i, j)) {
                    throw new IllegalArgumentException("Top-left finder pattern missing");
                }
                
                // Top-right
                if (reserved[i][size - 7 + j] && !matrix.get(i, size - 7 + j)) {
                    throw new IllegalArgumentException("Top-right finder pattern missing");
                }
                
                // Bottom-left
                if (reserved[size - 7 + i][j] && !matrix.get(size - 7 + i, j)) {
                    throw new IllegalArgumentException("Bottom-left finder pattern missing");
                }
            }
        }
        
        // Verify that no reserved cells that aren't part of finder patterns are true
        for (int i = 0; i < size; i++) {
            for (int j = 0; j < size; j++) {
                if (reserved[i][j] && !matrix.get(i, j)) {
                    throw new IllegalArgumentException("A required finder cell is false");
                }
            }
        }
    }
}