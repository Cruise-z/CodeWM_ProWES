/**
 * Core game engine managing snake movement, food placement, collisions, and scoring.
 * This class orchestrates all game rules and provides a canonical API for interaction.
 */
public final class SnakeGame {
    /** The width of the game grid. */
    private final int width;
    
    /** The height of the game grid. */
    private final int height;
    
    /** The snake entity managed by this game. */
    private Snake snake;
    
    /** Source of randomness for food placement. */
    private final RandomSource rng;
    
    /** Current movement direction of the snake. */
    private Direction direction;
    
    /** Position of the current food item. */
    private Position food;
    
    /** Current player score. */
    private int score;
    
    /** Flag indicating if the game has ended. */
    private boolean gameOver;

    /**
     * Creates a new SnakeGame with the specified dimensions and random source.
     * Initializes the snake at a valid starting position, score=0, and places food randomly.
     *
     * @param width the width of the game grid (must be positive)
     * @param height the height of the game grid (must be positive)
     * @param rng the source of randomness for food placement
     * @throws IllegalArgumentException if width or height are not positive
     */
    public SnakeGame(int width, int height, RandomSource rng) {
        if (width <= 0 || height <= 0) {
            throw new IllegalArgumentException("Width and height must be positive");
        }
        this.width = width;
        this.height = height;
        this.rng = rng;
        this.score = 0;
        this.gameOver = false;
        // Initialize snake at center with default direction
        int startX = width / 2;
        int startY = height / 2;
        this.snake = new Snake(new Position(startX, startY));
        this.direction = Direction.UP;
        placeFoodRandomly();
    }

    /**
     * Resets the game to its initial state with the same dimensions and random source.
     * The snake is placed at the center, score is reset to zero, and food is placed randomly.
     */
    public void reset() {
        int startX = width / 2;
        int startY = height / 2;
        this.snake = new Snake(new Position(startX, startY));
        this.direction = Direction.UP;
        this.score = 0;
        this.gameOver = false;
        placeFoodRandomly();
    }

    /**
     * Sets the intended movement direction for the snake, if it's not an immediate reversal.
     * 
     * @param dir the new direction to set; if null, the direction remains unchanged
     * @return true if the direction was accepted (not a reversal), false otherwise
     */
    public boolean setDirection(Direction dir) {
        if (dir == null) {
            return false;
        }
        if (direction.isOpposite(dir)) {
            return false;
        }
        this.direction = dir;
        return true;
    }

    /**
     * Gets the current movement direction of the snake.
     *
     * @return the current direction
     */
    public Direction getDirection() {
        return direction;
    }

    /**
     * Advances the game state by one tick.
     * Moves the snake one cell forward in its current direction.
     * If the new head position contains food, the snake grows and a new food is placed.
     * If the new head position is out of bounds or collides with the snake's body, the game ends.
     *
     * @return the outcome of the tick (MOVED, ATE_FOOD, or GAME_OVER)
     */
    public MoveOutcome tick() {
        if (gameOver) {
            return MoveOutcome.GAME_OVER;
        }
        
        Position newHead = snake.head().plus(direction.dx(), direction.dy());
        
        // Check for collisions with boundaries
        if (!inBounds(newHead)) {
            gameOver = true;
            return MoveOutcome.GAME_OVER;
        }
        
        // Check for collision with self
        if (snake.occupies(newHead)) {
            gameOver = true;
            return MoveOutcome.GAME_OVER;
        }
        
        // Check if food is eaten
        if (newHead.equals(food)) {
            snake.growTo(newHead);
            score++;
            placeFoodRandomly();
            return MoveOutcome.ATE_FOOD;
        } else {
            snake.moveTo(newHead);
            return MoveOutcome.MOVED;
        }
    }

    /**
     * Checks if a position is within the game grid boundaries.
     *
     * @param p the position to check
     * @return true if the position is within [0,width) x [0,height), false otherwise
     */
    private boolean inBounds(Position p) {
        return 0 <= p.getX() && p.getX() < width && 
               0 <= p.getY() && p.getY() < height;
    }

    /**
     * Places food at a random empty position on the grid.
     * If no empty positions remain, marks the game as over.
     */
    private void placeFoodRandomly() {
        // Find all empty positions
        java.util.List<Position> emptyPositions = new java.util.ArrayList<>();
        for (int x = 0; x < width; x++) {
            for (int y = 0; y < height; y++) {
                Position candidate = new Position(x, y);
                if (!snake.occupies(candidate)) {
                    emptyPositions.add(candidate);
                }
            }
        }
        
        // If no empty positions, game over
        if (emptyPositions.isEmpty()) {
            gameOver = true;
            return;
        }
        
        // Pick a random empty position
        int index = rng.nextInt(emptyPositions.size());
        food = emptyPositions.get(index);
    }

    /**
     * Determines whether the game has ended.
     *
     * @return true if the game is over, false otherwise
     */
    public boolean isGameOver() {
        return gameOver;
    }

    /**
     * Gets the current player score.
     *
     * @return the score
     */
    public int getScore() {
        return score;
    }

    /**
     * Gets the width of the game grid.
     *
     * @return the width
     */
    public int getWidth() {
        return width;
    }

    /**
     * Gets the height of the game grid.
     *
     * @return the height
     */
    public int getHeight() {
        return height;
    }

    /**
     * Creates an immutable snapshot of the current game state.
     *
     * @return a GameSnapshot containing the current state
     */
    public GameSnapshot snapshot() {
        return new GameSnapshot(width, height, snake.bodyAsList(), food, score, gameOver, direction);
    }

    /**
     * Places food at a specific position, replacing the existing food.
     * Useful for deterministic testing scenarios.
     *
     * @param p the position to place the food at
     * @throws IllegalArgumentException if p is out of bounds or occupied by the snake
     */
    public void placeFoodAt(Position p) {
        if (!inBounds(p)) {
            throw new IllegalArgumentException("Food position must be within bounds");
        }
        if (snake.occupies(p)) {
            throw new IllegalArgumentException("Food position cannot occupy snake body");
        }
        food = p;
    }
}