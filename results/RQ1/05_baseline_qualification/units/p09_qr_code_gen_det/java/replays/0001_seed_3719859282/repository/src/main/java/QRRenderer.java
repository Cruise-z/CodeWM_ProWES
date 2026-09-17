/**
 * Provides utilities for rendering QR code matrices as text.
 * Produces a deterministic string representation with exactly one line per matrix row.
 */
public class QRRenderer {
    
    /**
     * Renders a QRMatrix as a text string.
     * Each true cell is represented by '#', each false cell by '.'.
     * There is exactly one line per row in the matrix.
     * 
     * @param matrix the QRMatrix to render
     * @return a string representation of the matrix
     */
    public static String render(QRMatrix matrix) {
        int size = matrix.getSize();
        StringBuilder sb = new StringBuilder();
        
        for (int row = 0; row < size; row++) {
            for (int col = 0; col < size; col++) {
                if (matrix.get(row, col)) {
                    sb.append('#');
                } else {
                    sb.append('.');
                }
            }
            // Add newline after each row except the last one
            if (row < size - 1) {
                sb.append('\n');
            }
        }
        
        return sb.toString();
    }
}