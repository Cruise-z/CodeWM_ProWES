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
     * Creates a new Position with the specified coordinates.
     *
     * @param x the x-coordinate
     * @param y the y-coordinate
     * @return a new Position instance
     */
    public static Position of(int x, int y) {
        return new Position(x, y);
    }

    /**
     * Checks if this Position is equal to another object.
     *
     * @param obj the object to compare with
     * @return true if the objects are equal, false otherwise
     */
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

    /**
     * Returns the hash code value for this Position.
     *
     * @return the hash code value
     */
    @Override
    public int hashCode() {
        return java.util.Objects.hash(x, y);
    }

    /**
     * Returns a string representation of this Position.
     *
     * @return a string representation of this Position
     */
    @Override
    public String toString() {
        return String.format("Position{x=%d, y=%d}", x, y);
    }
}