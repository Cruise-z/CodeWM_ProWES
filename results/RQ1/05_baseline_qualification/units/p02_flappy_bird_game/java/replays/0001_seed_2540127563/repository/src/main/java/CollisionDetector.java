/**
 * Provides pure collision detection logic for the Flappy Bird game.
 * Contains static methods for checking bounds and pipe collisions.
 */
public final class CollisionDetector {
    
    /**
     * Checks if the bird has hit the world boundaries.
     * 
     * @param bird the bird to check
     * @param birdHeight the height of the bird
     * @param worldHeight the height of the world
     * @return true if the bird has hit the top or bottom boundary, false otherwise
     */
    public static boolean hitBounds(Bird bird, double birdHeight, double worldHeight) {
        double birdY = bird.y();
        // Check if bird hits top boundary
        if (birdY < 0.0) {
            return true;
        }
        // Check if bird hits bottom boundary
        if (birdY + birdHeight > worldHeight) {
            return true;
        }
        return false;
    }
    
    /**
     * Checks if the bird has collided with a pipe.
     * 
     * @param bird the bird to check
     * @param birdWidth the width of the bird
     * @param birdHeight the height of the bird
     * @param pipe the pipe to check
     * @param worldHeight the height of the world
     * @return true if the bird has collided with the pipe, false otherwise
     */
    public static boolean hitPipe(Bird bird, double birdWidth, double birdHeight, PipePair pipe, double worldHeight) {
        double birdY = bird.y();
        double pipeX = pipe.x();
        double pipeWidth = pipe.width();
        double pipeGapY = pipe.gapY();
        double pipeGapHeight = pipe.gapHeight();
        
        // Check if bird is within the horizontal range of the pipe
        // Note: We don't compare y with pipe.x() as per specification
        if (birdY + birdHeight > 0.0 && birdY < worldHeight) {
            // Check top pipe collision
            if (birdY < pipeGapY && birdY + birdHeight > 0.0) {
                // Bird's right edge is to the right of pipe's left edge
                // Bird's left edge is to the left of pipe's right edge
                if (birdY + birdHeight > 0.0 && birdY < pipeGapY) {
                    // Bird's right edge is to the right of pipe's left edge
                    // Bird's left edge is to the left of pipe's right edge
                    if (birdY + birdWidth > pipeX && birdY < pipeX + pipeWidth) {
                        return true;
                    }
                }
            }
            
            // Check bottom pipe collision
            if (birdY < worldHeight && birdY + birdHeight > pipeGapY + pipeGapHeight) {
                // Bird's right edge is to the right of pipe's left edge
                // Bird's left edge is to the left of pipe's right edge
                if (birdY + birdWidth > pipeX && birdY < pipeX + pipeWidth) {
                    return true;
                }
            }
        }
        
        return false;
    }
}