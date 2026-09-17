/**
 * Immutable snapshot of the game state at a particular moment.
 * This class provides a read-only view of the game for observers and tests.
 */
public final class GameSnapshot {
    /** The width of the game grid. */
    private final int width;
    
    /** The height of the game grid. */
    private final int height;
    
    /** The body of the snake as a list of positions, from head to tail. */
    private final java.util.List<Position> body;
    
    /** The position of the current food item. */
    private final Position food;
    
    /** The current score of the player. */
    private final int score;
    
    /** Whether the game is over. */
    private final boolean gameOver;
    
    /** The current direction of the snake's movement. */
    private final Direction direction;

    /**
     * Constructs a new GameSnapshot with the specified parameters.
     *
     * @param width the width of the game grid
     * @param height the height of the game grid
     * @param body the snake's body positions, from head to tail
     * @param food the position of the food
     * @param score the current score
     * @param gameOver whether the game is over
     * @param direction the current direction of movement
     * @throws NullPointerException if body or food is null
     * @throws IllegalArgumentException if width or height is not positive
     */
    public GameSnapshot(int width, int height, java.util.List<Position> body, Position food, int score, boolean gameOver, Direction direction) {
        if (width <= 0 || height <= 0) {
            throw new IllegalArgumentException("Width and height must be positive");
        }
        if (body == null) {
            throw new NullPointerException("Body cannot be null");
        }
        if (food == null) {
            throw new NullPointerException("Food cannot be null");
        }
        
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
     * Returns an unmodifiable view of the snake's body positions.
     * The positions are ordered from head to tail.
     *
     * @return the snake body positions
     */
    public java.util.List<Position> getSnakeBody() {
        return body;
    }

    /**
     * Returns the position of the current food item.
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

    @Override
    public String toString() {
        return String.format(
            "GameSnapshot{width=%d, height=%d, body=%s, food=%s, score=%d, gameOver=%s, direction=%s}",
            width,
            height,
            body,
            food,
            score,
            gameOver,
            direction
        );
    }
}