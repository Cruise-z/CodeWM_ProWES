/**
 * Orchestrates the game state, including world bounds, entity management,
 * physics integration, and collision handling.
 */
public final class Game {
    /** The width of the game world. */
    private final double width;
    
    /** The height of the game world. */
    private final double height;
    
    /** The paddle in the game. */
    private final Paddle paddle;
    
    /** The ball in the game. */
    private final Ball ball;
    
    /** The list of bricks in the game. */
    private final java.util.List<Brick> bricks;
    
    /** The number of lives remaining. */
    private int lives;
    
    /** The current score. */
    int score;
    
    /** Indicates whether the level has been completed. */
    boolean levelCompleted;
    
    /** Indicates whether a life was lost in the last tick. */
    boolean lifeLost;

    /**
     * Constructs a new game with the specified parameters.
     *
     * @param width    the width of the game world
     * @param height   the height of the game world
     * @param paddle   the paddle in the game
     * @param ball     the ball in the game
     * @param bricks   the list of bricks in the game
     * @param lives    the initial number of lives
     */
    public Game(double width, double height, Paddle paddle, Ball ball, java.util.List<Brick> bricks, int lives) {
        this.width = width;
        this.height = height;
        this.paddle = paddle;
        this.ball = ball;
        // Make a defensive copy while preserving object identities
        this.bricks = new java.util.ArrayList<>(bricks);
        this.lives = lives;
        this.score = 0;
        this.levelCompleted = false;
        this.lifeLost = false;
    }

    /**
     * Returns the number of lives remaining.
     *
     * @return the number of lives
     */
    public int getLives() {
        return lives;
    }

    /**
     * Checks if a life was lost in the last tick.
     *
     * @return true if a life was lost, false otherwise
     */
    public boolean isLifeLost() {
        return lifeLost;
    }

    /**
     * Checks if the level has been completed.
     *
     * @return true if the level is completed, false otherwise
     */
    public boolean isLevelCompleted() {
        return levelCompleted;
    }

    /**
     * Returns the current score.
     *
     * @return the score
     */
    public int getScore() {
        return score;
    }

    /**
     * Returns an unmodifiable view of the bricks list.
     *
     * @return the bricks list
     */
    public java.util.List<Brick> getBricks() {
        return java.util.Collections.unmodifiableList(bricks);
    }

    /**
     * Returns the paddle in the game.
     *
     * @return the paddle
     */
    public Paddle getPaddle() {
        return paddle;
    }

    /**
     * Returns the ball in the game.
     *
     * @return the ball
     */
    public Ball getBall() {
        return ball;
    }

    /**
     * Updates the game state by integrating physics and processing collisions.
     *
     * @param dt the time step to advance the simulation
     * @throws IllegalArgumentException if dt is not finite or not greater than 0
     */
    public void tick(double dt) {
        if (!Double.isFinite(dt) || dt <= 0) {
            throw new IllegalArgumentException("dt must be finite and greater than 0");
        }
        
        // Reset the lifeLost flag for this tick
        lifeLost = false;
        
        // Integrate the ball's position
        ball.setPosition(ball.getX() + ball.getVx() * dt, ball.getY() + ball.getVy() * dt);
        
        // Handle wall collisions
        handleWallCollisions();
        
        // If we lost a life due to bottom-out, skip further collision processing
        if (lifeLost) {
            return;
        }
        
        // Handle paddle collision
        handlePaddleCollision();
        
        // Handle brick collisions
        handleBrickCollisions();
        
        // Check if the level is completed
        updateLevelCompletion();
    }
    
    /**
     * Handles collisions with the walls of the game world.
     */
    private void handleWallCollisions() {
        double r = ball.getRadius();
        
        // Left wall collision
        if (ball.getX() - r <= 0) {
            ball.setVelocity(-ball.getVx(), ball.getVy());
            ball.setPosition(r, ball.getY());
        }
        // Right wall collision
        else if (ball.getX() + r >= width) {
            ball.setVelocity(-ball.getVx(), ball.getVy());
            ball.setPosition(width - r, ball.getY());
        }
        // Top wall collision
        else if (ball.getY() - r <= 0) {
            ball.setVelocity(ball.getVx(), -ball.getVy());
            ball.setPosition(ball.getX(), r);
        }
        // Bottom-out collision
        else if (ball.getY() - r >= height) {
            lives--;
            lifeLost = true;
            
            // Reset the ball to the paddle position
            ball.setPosition(paddle.getX(), 
                            paddle.getY() - paddle.getHeight() / 2 - r);
            ball.setVelocity(0, -Math.abs(ball.getVy()));
        }
    }
    
    /**
     * Handles collisions with the paddle.
     */
    private void handlePaddleCollision() {
        Rect paddleRect = paddle.asRect();
        
        if (Collision.circleIntersectsRect(ball.getX(), ball.getY(), ball.getRadius(), paddleRect)) {
            double[] penetration = Collision.penetration(ball.getX(), ball.getY(), ball.getRadius(), paddleRect);
            
            // Reflect along the axis with minimum penetration
            if (penetration[1] <= penetration[0]) {
                // Reflect vertically
                ball.setVelocity(ball.getVx(), -ball.getVy());
                // Move the ball out of the paddle along the Y axis
                ball.setPosition(ball.getX(), ball.getY() + penetration[1] * (ball.getY() < paddle.getY() ? 1 : -1));
            } else {
                // Reflect horizontally
                ball.setVelocity(-ball.getVx(), ball.getVy());
                // Move the ball out of the paddle along the X axis
                ball.setPosition(ball.getX() + penetration[0] * (ball.getX() < paddle.getX() ? 1 : -1), ball.getY());
            }
        }
    }
    
    /**
     * Handles collisions with bricks.
     */
    private void handleBrickCollisions() {
        // Create a copy of the bricks list to avoid concurrent modification issues
        java.util.List<Brick> bricksCopy = new java.util.ArrayList<>(bricks);
        
        for (Brick brick : bricksCopy) {
            if (Collision.circleIntersectsRect(ball.getX(), ball.getY(), ball.getRadius(), brick.getRect())) {
                double[] penetration = Collision.penetration(ball.getX(), ball.getY(), ball.getRadius(), brick.getRect());
                
                // Reflect along the axis with minimum penetration
                if (penetration[1] <= penetration[0]) {
                    // Reflect vertically
                    ball.setVelocity(ball.getVx(), -ball.getVy());
                    // Move the ball out of the brick along the Y axis
                    ball.setPosition(ball.getX(), ball.getY() + penetration[1] * (ball.getY() < brick.getRect().top() ? 1 : -1));
                } else {
                    // Reflect horizontally
                    ball.setVelocity(-ball.getVx(), ball.getVy());
                    // Move the ball out of the brick along the X axis
                    ball.setPosition(ball.getX() + penetration[0] * (ball.getX() < brick.getRect().left() ? 1 : -1), ball.getY());
                }
                
                // Process the hit
                brick.hit();
                
                // Remove the brick if it's breakable and destroyed
                if (brick.isBreakable() && brick.isDestroyed()) {
                    bricks.remove(brick);
                    score += 100;
                }
                
                // Only process the first collision in this tick
                break;
            }
        }
    }
    
    /**
     * Updates the level completion status based on remaining bricks.
     */
    private void updateLevelCompletion() {
        // Check if there are any breakable bricks that haven't been destroyed
        for (Brick brick : bricks) {
            if (brick.isBreakable() && !brick.isDestroyed()) {
                levelCompleted = false;
                return;
            }
        }
        // If we reach here, all breakable bricks are destroyed or non-breakable
        levelCompleted = true;
    }
}