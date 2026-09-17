/**
 * Immutable 2D coordinate representing a position in the game grid.
 */
public final class Position {
    /** The x-coordinate of this position. */
    private final int x;
    
    /** The y-coordinate of this position. */
    private final int y;

    /**
     * Constructs a new Position with the specified coordinates.
     *
     * @param x the x-coordinate
     * @param y the y-coordinate
     */
    public Position(int x, int y) {
        this.x = x;
        this.y = y;
    }

    /**
     * Returns the x-coordinate of this position.
     *
     * @return the x-coordinate
     */
    public int getX() {
        return x;
    }

    /**
     * Returns the y-coordinate of this position.
     *
     * @return the y-coordinate
     */
    public int getY() {
        return y;
    }

    /**
     * Returns a new Position with coordinates offset by the specified amounts.
     *
     * @param dx the amount to add to the x-coordinate
     * @param dy the amount to add to the y-coordinate
     * @return a new Position with the offset coordinates
     */
    public Position plus(int dx, int dy) {
        return new Position(x + dx, y + dy);
    }

    /**
     * Returns a new Position with the specified coordinates.
     *
     * @param x the x-coordinate
     * @param y the y-coordinate
     * @return a new Position with the specified coordinates
     */
    public static Position of(int x, int y) {
        return new Position(x, y);
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj) {
            return true;
        }
        if (obj == null || getClass() != obj.getClass()) {
            return false;
        }
        Position position = (Position) obj;
        return x == position.x && y == position.y;
    }

    @Override
    public int hashCode() {
        return 31 * x + y;
    }

    @Override
    public String toString() {
        return String.format("Position{x=%d, y=%d}", x, y);
    }
}