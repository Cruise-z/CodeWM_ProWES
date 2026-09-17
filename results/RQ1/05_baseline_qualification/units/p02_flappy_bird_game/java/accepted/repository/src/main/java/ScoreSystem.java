/**
 * Provides pure scoring logic for the Flappy Bird game.
 * Contains static methods for determining if a pipe has been passed.
 */
public final class ScoreSystem {
    
    /**
     * Determines if the bird has passed a pipe.
     * Returns true exactly once when the trailing edge of the pipe
     * (pipe.x() + pipe.width()) is strictly less than the bird's X position.
     * Marks the pipe as scored to prevent future scoring.
     * 
     * @param birdX the X position of the bird
     * @param pipe the pipe to check
     * @return true if the bird has passed the pipe for the first time, false otherwise
     */
    public static boolean passedPipe(double birdX, PipePair pipe) {
        // Check if pipe is already scored
        if (pipe.scored()) {
            return false;
        }
        
        // Check if bird has passed the pipe (trailing edge of pipe is to the left of bird)
        if (pipe.x() + pipe.width() < birdX) {
            // Mark pipe as scored
            pipe.markScored();
            return true;
        }
        
        return false;
    }
}