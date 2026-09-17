/**
 * Core game engine managing movement, reversal rule, growth, collisions, scoring, and food placement.
 * This class orchestrates all game rules and provides a canonical API for game state management.
 */
public final class SnakeGame {
    /** The width of the game grid. */
    private final int width;
    
    /** The height of the game grid. */
    private final int height;
    
    /** The snake representation. */
    private Snake snake;
    
    /** Random source for food placement. */
    private final RandomSource rng;
    
    /** Current movement direction of the snake. */
    private Direction direction;
    
    /** Current food position. */
    private Position food;
    
    /** Current score. */
    private int score;
    
    /** Whether the game has ended. */
    private boolean gameOver;

    /**
     * Constructs a new SnakeGame with the specified dimensions and random source.
     * Initializes the snake at a valid starting position, score to 0, and places food randomly.
     *
     * @param width the width of the game grid
     * @param height the height of the game grid
     * @param rng the random source for food placement
     * @throws IllegalArgumentException if width or height is not positive
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
        
        // Initialize snake at center of the grid
        Position start = new Position(width / 2, height / 2);
        this.snake = new Snake(start);
        this.direction = Direction.UP;
        placeFoodRandomly();
    }

    /**
     * Resets the game to its initial state using the same parameters.
     * The snake is placed back at the starting position, score is reset to 0,
     * and food is placed randomly again.
     */
    public void reset() {
        this.score = 0;
        this.gameOver = false;
        Position start = new Position(width / 2, height / 2);
        this.snake = new Snake(start);
        this.direction = Direction.UP;
        placeFoodRandomly();
    }

    /**
     * Sets the intended movement direction for the snake.
     * Rejects immediate reversals (e.g., if currently going UP, DOWN is not allowed).
     *
     * @param dir the new direction to set
     * @return true if the direction was accepted, false if rejected due to reversal rule
     */
    public boolean setDirection(Direction dir) {
        if (dir == null) {
            return false;
        }
        if (dir.isOpposite(this.direction)) {
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
        return this.direction;
    }

    /**
     * Advances the game state by one tick.
     * Processes movement, food consumption, collisions, and scoring.
     *
     * @return the outcome of this tick (MOVED, ATE_FOOD, or GAME_OVER)
     */
    public MoveOutcome tick() {
        if (gameOver) {
            return MoveOutcome.GAME_OVER;
        }
        
        Position nextHead = snake.head().plus(direction.dx(), direction.dy());
        
        // Check for out-of-bounds
        if (!inBounds(nextHead)) {
            gameOver = true;
            return MoveOutcome.GAME_OVER;
        }
        
        // Check for self-collision
        if (snake.occupies(nextHead)) {
            gameOver = true;
            return MoveOutcome.GAME_OVER;
        }
        
        // Move snake
        if (nextHead.equals(food)) {
            // Eat food
            snake.growTo(nextHead);
            score++;
            placeFoodRandomly();
            return MoveOutcome.ATE_FOOD;
        } else {
            // Normal move
            snake.moveTo(nextHead);
            return MoveOutcome.MOVED;
        }
    }

    /**
     * Checks if a position is within the game boundaries.
     *
     * @param p the position to check
     * @return true if the position is within the grid, false otherwise
     */
    private boolean inBounds(Position p) {
        return p.getX() >= 0 && p.getX() < width && p.getY() >= 0 && p.getY() < height;
    }

    /**
     * Places food at a random empty position.
     * If no free positions remain, sets game over to true.
     */
    private void placeFoodRandomly() {
        // Find all free positions
        java.util.List<Position> freePositions = new java.util.ArrayList<>();
        for (int x = 0; x < width; x++) {
            for (int y = 0; y < height; y++) {
                Position pos = new Position(x, y);
                if (!snake.occupies(pos)) {
                    freePositions.add(pos);
                }
            }
        }
        
        // If no free positions, game over
        if (freePositions.isEmpty()) {
            gameOver = true;
            return;
        }
        
        // Choose random position from free positions
        int index = rng.nextInt(freePositions.size());
        this.food = freePositions.get(index);
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
     * Gets the current score.
     *
     * @return the current score
     */
    public int getScore() {
        return score;
    }

    /**
     * Gets the width of the game grid.
     *
     * @return the grid width
     */
    public int getWidth() {
        return width;
    }

    /**
     * Gets the height of the game grid.
     *
     * @return the grid height
     */
    public int getHeight() {
        return height;
    }

    /**
     * Gets an immutable snapshot of the current game state.
     *
     * @return a snapshot of the current game state
     */
    public GameSnapshot snapshot() {
        return new GameSnapshot(
            width,
            height,
            snake.bodyAsList(),
            food,
            score,
            gameOver,
            direction
        );
    }

    /**
     * Places food at a specified position, overriding the current food position.
     * Validates that the position is within bounds and not occupied by the snake.
     *
     * @param p the new food position
     * @throws IllegalArgumentException if position is out of bounds or occupied
     */
    public void placeFoodAt(Position p) {
        if (!inBounds(p)) {
            throw new IllegalArgumentException("Food position is out of bounds");
        }
        if (snake.occupies(p)) {
            throw new IllegalArgumentException("Food position is occupied by snake");
        }
        this.food = p;
    }
}