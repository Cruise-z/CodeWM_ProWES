/**
 * Represents a brick in the game with rectangular bounds, hit points, and breakability.
 */
public final class Brick {
    /** The rectangular bounds of the brick. */
    private final Rect rect;
    
    /** The number of hit points the brick has before being destroyed. */
    private int hitPoints;
    
    /** Indicates whether the brick can be broken (removed) when hit. */
    private final boolean breakable;

    /**
     * Constructs a new brick with the specified properties.
     *
     * @param rect      the rectangular bounds of the brick
     * @param hitPoints the number of hit points the brick has (must be non-negative)
     * @param breakable indicates whether the brick can be broken (removed) when hit
     */
    public Brick(Rect rect, int hitPoints, boolean breakable) {
        this.rect = rect;
        this.hitPoints = hitPoints;
        this.breakable = breakable;
    }

    /**
     * Returns the rectangular bounds of the brick.
     *
     * @return the rectangle representing the brick's bounds
     */
    public Rect getRect() {
        return rect;
    }

    /**
     * Returns the number of hit points the brick has.
     *
     * @return the hit points
     */
    public int getHitPoints() {
        return hitPoints;
    }

    /**
     * Checks if the brick is breakable (can be removed when hit).
     *
     * @return true if the brick is breakable, false otherwise
     */
    public boolean isBreakable() {
        return breakable;
    }

    /**
     * Processes a hit on the brick, reducing its hit points by 1.
     * If hitPoints was greater than 0, it is decremented by 1.
     * Hit points are never allowed to go below 0.
     * This method has no effect if hitPoints is already 0.
     */
    public void hit() {
        if (hitPoints > 0) {
            hitPoints--;
        }
    }

    /**
     * Checks if the brick is destroyed (has 0 hit points).
     *
     * @return true if the brick is destroyed, false otherwise
     */
    public boolean isDestroyed() {
        return hitPoints == 0;
    }
}