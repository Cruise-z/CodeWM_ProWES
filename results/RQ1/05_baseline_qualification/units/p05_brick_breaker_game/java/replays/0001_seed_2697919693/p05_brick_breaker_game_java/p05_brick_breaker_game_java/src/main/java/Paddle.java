/**
 * Represents a paddle in the game with center position, dimensions, and movement constraints.
 */
public final class Paddle {
    /** The x-coordinate of the paddle's center. */
    private double x;
    
    /** The y-coordinate of the paddle's center. */
    private double y;
    
    /** The width of the paddle. */
    private final double width;
    
    /** The height of the paddle. */
    private final double height;
    
    /** The maximum x-coordinate the paddle center can reach. */
    private final double maxX;

    /**
     * Constructs a new paddle with the specified properties.
     *
     * @param x      the x-coordinate of the paddle's center
     * @param y      the y-coordinate of the paddle's center
     * @param width  the width of the paddle (must be positive)
     * @param height the height of the paddle (must be positive)
     * @param maxX   the maximum x-coordinate the paddle center can reach
     */
    public Paddle(double x, double y, double width, double height, double maxX) {
        this.x = x;
        this.y = y;
        this.width = width;
        this.height = height;
        this.maxX = maxX;
        // Ensure the paddle is initially within bounds
        setX(x);
    }

    /**
     * Returns the x-coordinate of the paddle's center.
     *
     * @return the x-coordinate
     */
    public double getX() {
        return x;
    }

    /**
     * Returns the y-coordinate of the paddle's center.
     *
     * @return the y-coordinate
     */
    public double getY() {
        return y;
    }

    /**
     * Returns the width of the paddle.
     *
     * @return the width
     */
    public double getWidth() {
        return width;
    }

    /**
     * Returns the height of the paddle.
     *
     * @return the height
     */
    public double getHeight() {
        return height;
    }

    /**
     * Sets the x-coordinate of the paddle's center, clamping it within valid bounds.
     * The paddle's center is constrained to be within [width/2, maxX - width/2].
     *
     * @param x the new x-coordinate of the paddle's center
     */
    public void setX(double x) {
        // Clamp the x-coordinate to ensure the paddle stays within the world bounds
        this.x = Math.max(width / 2, Math.min(maxX - width / 2, x));
    }

    /**
     * Returns the rectangle representation of the paddle.
     * The returned rectangle has its top-left corner at (x - width/2, y - height/2).
     *
     * @return the rectangle representation of the paddle
     */
    public Rect asRect() {
        return new Rect(x - width / 2, y - height / 2, width, height);
    }
}