/**
 * Provides collision detection and response utilities for circular objects
 * and axis-aligned rectangles.
 */
public final class Collision {
    
    /**
     * Determines if a circle intersects with an axis-aligned rectangle.
     * The intersection is inclusive - if the circle touches the rectangle's
     * boundary, it is considered intersecting.
     *
     * @param cx     the x-coordinate of the circle's center
     * @param cy     the y-coordinate of the circle's center
     * @param r      the radius of the circle (must be non-negative)
     * @param rect   the rectangle to test intersection with
     * @return true if the circle and rectangle intersect, false otherwise
     */
    public static boolean circleIntersectsRect(double cx, double cy, double r, Rect rect) {
        // Find the closest point on the rectangle to the circle's center
        double closestX = Math.max(rect.left(), Math.min(cx, rect.right()));
        double closestY = Math.max(rect.top(), Math.min(cy, rect.bottom()));
        
        // Calculate the distance between the circle's center and this closest point
        double distanceX = cx - closestX;
        double distanceY = cy - closestY;
        
        // If the distance is less than or equal to the radius, they intersect
        return (distanceX * distanceX + distanceY * distanceY) <= (r * r);
    }
    
    /**
     * Calculates the penetration depth of a circle into a rectangle along both axes.
     * This method assumes that an intersection exists (i.e., circleIntersectsRect returned true).
     * The penetration values indicate how far the circle needs to be moved along each axis
     * to resolve the collision.
     *
     * @param cx     the x-coordinate of the circle's center
     * @param cy     the y-coordinate of the circle's center
     * @param r      the radius of the circle (must be non-negative)
     * @param rect   the rectangle the circle is penetrating
     * @return an array of two doubles: {penX, penY} where penX is the horizontal
     *         penetration depth and penY is the vertical penetration depth.
     *         Both values are non-negative.
     */
    public static double[] penetration(double cx, double cy, double r, Rect rect) {
        // Find the closest point on the rectangle to the circle's center
        double closestX = Math.max(rect.left(), Math.min(cx, rect.right()));
        double closestY = Math.max(rect.top(), Math.min(cy, rect.bottom()));
        
        // Calculate the penetration depths along each axis
        double penX = r - Math.abs(cx - closestX);
        double penY = r - Math.abs(cy - closestY);
        
        // Ensure non-negative values
        penX = Math.max(0, penX);
        penY = Math.max(0, penY);
        
        return new double[]{penX, penY};
    }
}