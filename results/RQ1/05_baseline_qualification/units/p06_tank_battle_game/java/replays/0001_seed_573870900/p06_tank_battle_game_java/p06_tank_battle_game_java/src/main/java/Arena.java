/**
 * Arena bounds and obstacles with validation and defensive copy.
 */
public class Arena {
    private final int width;
    private final int height;
    private final ObstacleMap obstacles;

    /**
     * Creates a new arena with the given dimensions and obstacles.
     *
     * @param width the width of the arena
     * @param height the height of the arena
     * @param obstacles the obstacle map for this arena
     * @throws IllegalArgumentException if width or height is not positive,
     *                                  or if obstacles is null
     */
    public Arena(int width, int height, ObstacleMap obstacles) {
        if (width <= 0) {
            throw new IllegalArgumentException("Arena width must be positive");
        }
        if (height <= 0) {
            throw new IllegalArgumentException("Arena height must be positive");
        }
        if (obstacles == null) {
            throw new IllegalArgumentException("Arena obstacles cannot be null");
        }

        this.width = width;
        this.height = height;
        this.obstacles = obstacles.copy();
    }

    /**
     * Checks if the given position is within the bounds of this arena.
     *
     * @param p the position to check
     * @return true if the position is within bounds, false otherwise
     */
    public boolean inBounds(Position p) {
        return p.getX() >= 0 && p.getX() < width && p.getY() >= 0 && p.getY() < height;
    }

    /**
     * Checks if there is an obstacle at the given position.
     *
     * @param p the position to check
     * @return true if there is an obstacle at the position, false otherwise
     */
    public boolean isObstacle(Position p) {
        return obstacles.isBlocked(p);
    }

    /**
     * Creates a copy of this arena.
     *
     * @return a new arena with the same dimensions and obstacles
     */
    public Arena copy() {
        return new Arena(width, height, obstacles);
    }
}