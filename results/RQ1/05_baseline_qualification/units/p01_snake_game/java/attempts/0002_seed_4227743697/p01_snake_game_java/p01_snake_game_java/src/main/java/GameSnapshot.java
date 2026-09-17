/**
 * Immutable snapshot of the game state at a point in time.
 * This class provides a read-only view of the game for observers and tests.
 */
public final class GameSnapshot {
    /** The width of the game grid. */
    private final int width;
    
    /** The height of the game grid. */
    private final int height;
    
    /** The body of the snake as a list of positions, head first. */
    private final java.util.List<Position> snakeBody;
    
    /** The position of the current food item. */
    private final Position food;
    
    /** The current score of the player. */
    private final int score;
    
    /** Whether the game is over. */
    private final boolean gameOver;
    
    /** The current direction of the snake's movement. */
    private final Direction direction;

    /**
     * Creates a new GameSnapshot with the specified parameters.
     *
     * @param width the width of the game grid
     * @param height the height of the game grid
     * @param body the snake's body as a list of positions (head first)
     * @param food the position of the food
     * @param score the current score
     * @param gameOver whether the game is over
     * @param direction the current direction of movement
     * @throws NullPointerException if body or food is null
     * @throws IllegalArgumentException if width or height are not positive
     */
    public GameSnapshot(
            int width, 
            int height, 
            java.util.List<Position> body, 
            Position food, 
            int score, 
            boolean gameOver, 
            Direction direction) {
        if (width <= 0 || height <= 0) {
            throw new IllegalArgumentException("Width and height must be positive");
        }
        this.width = width;
        this.height = height;
        this.snakeBody = new java.util.ArrayList<>(body);
        this.food = food;
        this.score = score;
        this.gameOver = gameOver;
        this.direction = direction;
    }

    /**
     * Returns the width of the game grid.
     *
     * @return the width
     */
    public int getWidth() {
        return width;
    }

    /**
     * Returns the height of the game grid.
     *
     * @return the height
     */
    public int getHeight() {
        return height;
    }

    /**
     * Returns an unmodifiable copy of the snake's body.
     * The positions are ordered from head to tail.
     *
     * @return an unmodifiable list of the snake's body positions
     */
    public java.util.List<Position> getSnakeBody() {
        return java.util.Collections.unmodifiableList(snakeBody);
    }

    /**
     * Returns the position of the food.
     *
     * @return the food position
     */
    public Position getFood() {
        return food;
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
     * Returns whether the game is over.
     *
     * @return true if the game is over, false otherwise
     */
    public boolean isGameOver() {
        return gameOver;
    }

    /**
     * Returns the current direction of the snake's movement.
     *
     * @return the direction
     */
    public Direction getDirection() {
        return direction;
    }

    /**
     * Returns a string representation of this GameSnapshot.
     * The format is concise for debugging and logging purposes.
     *
     * @return a string representation of this snapshot
     */
    @Override
    public String toString() {
        return String.format(
            "GameSnapshot{width=%d, height=%d, snakeBody=%s, food=%s, score=%d, gameOver=%b, direction=%s}",
            width,
            height,
            snakeBody,
            food,
            score,
            gameOver,
            direction
        );
    }
}