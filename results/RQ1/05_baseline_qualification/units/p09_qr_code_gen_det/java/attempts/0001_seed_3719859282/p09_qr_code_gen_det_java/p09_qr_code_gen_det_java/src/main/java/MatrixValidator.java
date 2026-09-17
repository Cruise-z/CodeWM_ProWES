/**
 * Provides validation utilities for QR code matrix dimensions and capacity calculations.
 */
public class MatrixValidator {
    
    /**
     * Ensures the given size is valid for a QR code matrix.
     * Valid sizes must be odd integers greater than or equal to 21.
     *
     * @param size the size to validate
     * @throws IllegalArgumentException if size is less than 21 or even
     */
    public static void ensureValidSize(int size) {
        if (size < 21) {
            throw new IllegalArgumentException("Size must be at least 21");
        }
        if (size % 2 == 0) {
            throw new IllegalArgumentException("Size must be odd");
        }
    }
    
    /**
     * Calculates the maximum number of data bits that can be stored in a QR code matrix of the given size.
     * This is derived by counting the number of unreserved cells (false entries) in the finder pattern reserved mask,
     * and rounding down to the nearest multiple of 8.
     *
     * @param size the size of the QR code matrix
     * @return the maximum number of data bits that can be stored
     */
    public static int capacityBits(int size) {
        // Ensure the size is valid
        ensureValidSize(size);
        
        // Get the reserved mask to determine unreserved cells
        boolean[][] reserved = FinderPattern.reservedMask(size);
        
        // Count unreserved cells
        int unreservedCount = 0;
        for (int i = 0; i < size; i++) {
            for (int j = 0; j < size; j++) {
                if (!reserved[i][j]) {
                    unreservedCount++;
                }
            }
        }
        
        // Round down to the nearest multiple of 8
        return (unreservedCount / 8) * 8;
    }
}