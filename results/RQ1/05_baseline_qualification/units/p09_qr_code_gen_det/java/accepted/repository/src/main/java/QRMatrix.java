/**
 * Represents a square matrix of boolean QR code modules.
 * The size is immutable after construction.
 */
public class QRMatrix {
    private final int size;
    private final boolean[][] cells;

    /**
     * Constructs a new QRMatrix of the specified size.
     *
     * @param size the size of the square matrix (must be positive)
     * @throws IllegalArgumentException if size is not positive
     */
    public QRMatrix(int size) {
        if (size <= 0) {
            throw new IllegalArgumentException("Size must be positive");
        }
        this.size = size;
        this.cells = new boolean[size][size];
    }

    /**
     * Returns the size of this matrix.
     *
     * @return the size of the matrix
     */
    public int getSize() {
        return size;
    }

    /**
     * Gets the value at the specified position.
     *
     * @param row the row index
     * @param col the column index
     * @return the value at the specified position
     * @throws IndexOutOfBoundsException if row or col is out of bounds
     */
    public boolean get(int row, int col) {
        if (row < 0 || row >= size || col < 0 || col >= size) {
            throw new IndexOutOfBoundsException(
                "Row and column must be between 0 and " + (size - 1));
        }
        return cells[row][col];
    }

    /**
     * Sets the value at the specified position.
     *
     * @param row the row index
     * @param col the column index
     * @param val the value to set
     * @throws IndexOutOfBoundsException if row or col is out of bounds
     */
    public void set(int row, int col, boolean val) {
        if (row < 0 || row >= size || col < 0 || col >= size) {
            throw new IndexOutOfBoundsException(
                "Row and column must be between 0 and " + (size - 1));
        }
        cells[row][col] = val;
    }

    /**
     * Creates a deep copy of the internal cells array.
     *
     * @return a deep copy of the cells array
     */
    public boolean[][] copyCells() {
        boolean[][] copy = new boolean[size][size];
        for (int i = 0; i < size; i++) {
            System.arraycopy(cells[i], 0, copy[i], 0, size);
        }
        return copy;
    }
}