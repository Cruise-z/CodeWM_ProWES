/**
 * Immutable grid coordinate with value semantics and translation.
 */
public class Position {
    private final int x;
    private final int y;

    /**
     * Creates a new position with the given coordinates.
     *
     * @param x the x-coordinate
     * @param y the y-coordinate
     */
    public Position(int x, int y) {
        this.x = x;
        this.y = y;
    }

    /**
     * Returns the x-coordinate.
     *
     * @return the x-coordinate
     */
    public int getX() {
        return x;
    }

    /**
     * Returns the y-coordinate.
     *
     * @return the y-coordinate
     */
    public int getY() {
        return y;
    }

    /**
     * Returns a new position that is translated by the given deltas.
     *
     * @param dx the change in x-coordinate
     * @param dy the change in y-coordinate
     * @return a new Position instance with translated coordinates
     */
    public Position translate(int dx, int dy) {
        return new Position(x + dx, y + dy);
    }

    /**
     * Checks if this position is equal to another object.
     *
     * @param o the object to compare with
     * @return true if the objects are equal, false otherwise
     */
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        Position position = (Position) o;

        if (x != position.x) return false;
        return y == position.y;
    }

    /**
     * Returns the hash code value for this position.
     *
     * @return the hash code value
     */
    @Override
    public int hashCode() {
        int result = x;
        result = 31 * result + y;
        return result;
    }
}