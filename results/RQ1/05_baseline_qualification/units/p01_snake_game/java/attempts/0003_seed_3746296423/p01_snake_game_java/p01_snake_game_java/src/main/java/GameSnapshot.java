/**
 * Immutable snapshot of the game state at a particular moment.
 * This class provides a read-only view of the game for observers and tests.
 */
public final class GameSnapshot {
    /** The width of the game grid. */
    private final int width;
    
    /** The height of the game grid. */
    private final int height;
    
    /** The current body of the snake, as a defensive copy. */
    private final java.util.List<Position> body;
    
    /** The current position of the food. */
    private final Position food;
    
    /** The current score of the player. */
    private final int score;
    
    /** Whether the game has ended. */
    private final boolean gameOver;
    
    /** The current direction of the snake's movement. */
    private final Direction direction;

    /**
     * Constructs a new GameSnapshot with the specified parameters.
     *
     * @param width the width of the game grid
     * @param height the height of the game grid
     * @param body the snake's body positions (must be defensive copy)
     * @param food the current food position
     * @param score the current score
     * @param gameOver whether the game has ended
     * @param direction the current direction of movement
     */
    public GameSnapshot(
            int width,
            int height,
            java.util.List<Position> body,
            Position food,
            int score,
            boolean gameOver,
            Direction direction) {
        this.width = width;
        this.height = height;
        this.body = java.util.Collections.unmodifiableList(new java.util.ArrayList<>(body));
        this.food = food;
        this.score = score;
        this.gameOver = gameOver;
        this.direction = direction;
    }

    /**
     * Returns the width of the game grid.
     *
     * @return the grid width
     */
    public int getWidth() {
        return width;
    }

    /**
     * Returns the height of the game grid.
     *
     * @return the grid height
     */
    public int getHeight() {
        return height;
    }

    /**
     * Returns an unmodifiable view of the snake's body positions.
     * Positions are ordered from head to tail.
     *
     * @return the snake body positions
     */
    public java.util.List<Position> getSnakeBody() {
        return body;
    }

    /**
     * Returns the current position of the food.
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
     * Checks if the game has ended.
     *
     * @return true if the game is over, false otherwise
     */
    public boolean isGameOver() {
        return gameOver;
    }

    /**
     * Returns the current direction of the snake's movement.
     *
     * @return the movement direction
     */
    public Direction getDirection() {
        return direction;
    }

    /**
     * Returns a string representation of this game snapshot.
     * Format: "GameSnapshot{width=..., height=..., body=..., food=..., score=..., gameOver=..., direction=...}"
     *
     * @return a string representation of this snapshot
     */
    @Override
    public String toString() {
        return String.format(
                "GameSnapshot{width=%d, height=%d, body=%s, food=%s, score=%d, gameOver=%b, direction=%s}",
                width,
                height,
                body,
                food,
                score,
                gameOver,
                direction);
    }
}