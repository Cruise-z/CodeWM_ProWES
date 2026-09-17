/**
 * Represents the bird in the Flappy Bird game with physics properties and behaviors.
 */
public class Bird {
    /** The vertical position of the bird. */
    private double y;
    
    /** The vertical velocity of the bird. */
    private double vy;

    /**
     * Creates a new bird at the specified starting Y position.
     *
     * @param startY the initial Y position of the bird
     */
    public Bird(double startY) {
        this.y = startY;
        this.vy = 0.0;
    }

    /**
     * Gets the current Y position of the bird.
     *
     * @return the Y position
     */
    public double y() {
        return this.y;
    }

    /**
     * Gets the current Y velocity of the bird.
     *
     * @return the Y velocity
     */
    public double vy() {
        return this.vy;
    }

    /**
     * Applies gravity to the bird's velocity.
     * Gravity increases velocity by +0.5 per tick, clamped to [-10.0, 10.0].
     */
    public void applyGravity() {
        this.vy = Math.max(-10.0, Math.min(10.0, this.vy + 0.5));
    }

    /**
     * Updates the bird's position based on its current velocity.
     * This should be called after applyGravity().
     */
    public void integrate() {
        this.y += this.vy;
    }

    /**
     * Makes the bird flap, setting its vertical velocity to -8.0.
     * This overrides any existing vertical velocity.
     */
    public void flap() {
        this.vy = -8.0;
    }
}