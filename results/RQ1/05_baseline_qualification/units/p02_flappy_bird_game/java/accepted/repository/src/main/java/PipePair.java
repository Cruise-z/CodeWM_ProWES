/**
 * Represents a pair of pipes (top and bottom) in the Flappy Bird game.
 */
public class PipePair {
    /** The x-coordinate of the pipe pair */
    private double x;
    
    /** The width of the pipe */
    private double width;
    
    /** The y-coordinate of the top pipe's bottom edge */
    private double gapY;
    
    /** The height of the gap between pipes */
    private double gapHeight;
    
    /** The speed at which the pipes move */
    private double speed;
    
    /** Flag indicating whether the bird has passed this pipe */
    private boolean scored;

    /**
     * Creates a new pipe pair with the specified properties.
     *
     * @param x the x-coordinate of the pipe pair
     * @param width the width of the pipe
     * @param gapY the y-coordinate of the top pipe's bottom edge
     * @param gapHeight the height of the gap between pipes
     * @param speed the speed at which the pipes move
     */
    public PipePair(double x, double width, double gapY, double gapHeight, double speed) {
        this.x = x;
        this.width = width;
        this.gapY = gapY;
        this.gapHeight = gapHeight;
        this.speed = speed;
        this.scored = false;
    }

    /**
     * Gets the x-coordinate of the pipe pair.
     *
     * @return the x-coordinate
     */
    public double x() {
        return this.x;
    }

    /**
     * Gets the width of the pipe.
     *
     * @return the width
     */
    public double width() {
        return this.width;
    }

    /**
     * Gets the y-coordinate of the top pipe's bottom edge.
     *
     * @return the gapY
     */
    public double gapY() {
        return this.gapY;
    }

    /**
     * Gets the height of the gap between pipes.
     *
     * @return the gapHeight
     */
    public double gapHeight() {
        return this.gapHeight;
    }

    /**
     * Gets the speed at which the pipes move.
     *
     * @return the speed
     */
    public double speed() {
        return this.speed;
    }

    /**
     * Checks if the bird has passed this pipe.
     *
     * @return true if the bird has passed this pipe, false otherwise
     */
    public boolean scored() {
        return this.scored;
    }

    /**
     * Marks this pipe as scored.
     * This should be called once when the bird passes the pipe.
     */
    public void markScored() {
        this.scored = true;
    }

    /**
     * Moves the pipe pair to the left by the speed amount.
     * This should be called each tick to update the pipe position.
     */
    public void move() {
        this.x -= this.speed;
    }
}