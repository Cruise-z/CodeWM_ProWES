/**
 * Represents a ball in the game with position, velocity, and radius.
 */
public final class Ball {
    /** The x-coordinate of the ball's center. */
    private double x;
    
    /** The y-coordinate of the ball's center. */
    private double y;
    
    /** The velocity in the x-direction. */
    private double vx;
    
    /** The velocity in the y-direction. */
    private double vy;
    
    /** The radius of the ball. */
    private final double radius;

    /**
     * Constructs a new ball with the specified properties.
     *
     * @param x      the x-coordinate of the ball's center
     * @param y      the y-coordinate of the ball's center
     * @param vx     the velocity in the x-direction
     * @param vy     the velocity in the y-direction
     * @param radius the radius of the ball (must be positive)
     */
    public Ball(double x, double y, double vx, double vy, double radius) {
        this.x = x;
        this.y = y;
        this.vx = vx;
        this.vy = vy;
        this.radius = radius;
    }

    /**
     * Returns the x-coordinate of the ball's center.
     *
     * @return the x-coordinate
     */
    public double getX() {
        return x;
    }

    /**
     * Returns the y-coordinate of the ball's center.
     *
     * @return the y-coordinate
     */
    public double getY() {
        return y;
    }

    /**
     * Returns the velocity in the x-direction.
     *
     * @return the x-velocity
     */
    public double getVx() {
        return vx;
    }

    /**
     * Returns the velocity in the y-direction.
     *
     * @return the y-velocity
     */
    public double getVy() {
        return vy;
    }

    /**
     * Returns the radius of the ball.
     *
     * @return the radius
     */
    public double getRadius() {
        return radius;
    }

    /**
     * Sets the position of the ball.
     * This method is package-private to allow tests to set the ball's position.
     *
     * @param x the new x-coordinate of the ball's center
     * @param y the new y-coordinate of the ball's center
     */
    void setPosition(double x, double y) {
        this.x = x;
        this.y = y;
    }

    /**
     * Sets the velocity of the ball.
     * This method is package-private to allow tests to set the ball's velocity.
     *
     * @param vx the new x-velocity
     * @param vy the new y-velocity
     */
    void setVelocity(double vx, double vy) {
        this.vx = vx;
        this.vy = vy;
    }
}