/**
 * An immutable axis-aligned bounding box (AABB) rectangle.
 */
public final class Rect {
    /** The x-coordinate of the top-left corner. */
    public final double x;
    
    /** The y-coordinate of the top-left corner. */
    public final double y;
    
    /** The width of the rectangle. */
    public final double width;
    
    /** The height of the rectangle. */
    public final double height;

    /**
     * Constructs a new rectangle with the specified properties.
     *
     * @param x      the x-coordinate of the top-left corner
     * @param y      the y-coordinate of the top-left corner
     * @param width  the width of the rectangle (must be non-negative)
     * @param height the height of the rectangle (must be non-negative)
     */
    public Rect(double x, double y, double width, double height) {
        this.x = x;
        this.y = y;
        this.width = width;
        this.height = height;
    }

    /**
     * Returns the x-coordinate of the left edge of the rectangle.
     *
     * @return the left edge x-coordinate
     */
    public double left() {
        return x;
    }

    /**
     * Returns the y-coordinate of the top edge of the rectangle.
     *
     * @return the top edge y-coordinate
     */
    public double top() {
        return y;
    }

    /**
     * Returns the x-coordinate of the right edge of the rectangle.
     *
     * @return the right edge x-coordinate
     */
    public double right() {
        return x + width;
    }

    /**
     * Returns the y-coordinate of the bottom edge of the rectangle.
     *
     * @return the bottom edge y-coordinate
     */
    public double bottom() {
        return y + height;
    }
}