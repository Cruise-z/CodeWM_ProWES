/**
 * Cardinal directions with dx/dy and left/right rotation.
 */
public enum Orientation {
    NORTH(0, -1),
    EAST(1, 0),
    SOUTH(0, 1),
    WEST(-1, 0);

    private final int dx;
    private final int dy;

    /**
     * Creates a new orientation with the given delta values.
     *
     * @param dx the change in x-coordinate for this orientation
     * @param dy the change in y-coordinate for this orientation
     */
    Orientation(int dx, int dy) {
        this.dx = dx;
        this.dy = dy;
    }

    /**
     * Returns the change in x-coordinate for this orientation.
     *
     * @return the change in x-coordinate
     */
    public int dx() {
        return dx;
    }

    /**
     * Returns the change in y-coordinate for this orientation.
     *
     * @return the change in y-coordinate
     */
    public int dy() {
        return dy;
    }

    /**
     * Returns the orientation that is to the left of this orientation.
     *
     * @return the left orientation
     */
    public Orientation left() {
        switch (this) {
            case NORTH: return WEST;
            case EAST:  return NORTH;
            case SOUTH: return EAST;
            case WEST:  return SOUTH;
            default: throw new AssertionError("Unknown orientation: " + this);
        }
    }

    /**
     * Returns the orientation that is to the right of this orientation.
     *
     * @return the right orientation
     */
    public Orientation right() {
        switch (this) {
            case NORTH: return EAST;
            case EAST:  return SOUTH;
            case SOUTH: return WEST;
            case WEST:  return NORTH;
            default: throw new AssertionError("Unknown orientation: " + this);
        }
    }
}