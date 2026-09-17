/**
 * Core game engine managing movement, reversal rule, growth, collisions, scoring, and food placement.
 * This class orchestrates the game logic and exposes a stable API for interaction.
 */
public final class SnakeGame {
    /** The width of the game grid. */
    private final int width;
    
    /** The height of the game grid. */
    private final int height;
    
    /** The snake object representing the player's character. */
    private Snake snake;
    
    /** Random number generator for placing food. */
    private final RandomSource rng;
    
    /** Current movement direction of the snake. */
    private Direction direction;
    
    /** Position of the currently active food item. */
    private Position food;
    
    /** Current score of the player. */
    private int score;
    
    /** Flag indicating whether the game has ended. */
    private boolean gameOver;

    /**
     * Constructs a new SnakeGame with the specified dimensions and random source.
     * Initializes the game with a snake at a valid starting position, score=0,
     * gameOver=false, and a randomly placed food.
     *
     * @param width the width of the game grid (must be positive)
     * @param height the height of the game grid (must be positive)
     * @param rng the random source for placing food
     * @throws IllegalArgumentException if width or height are not positive
     */
    public SnakeGame(int width, int height, RandomSource rng) {
        if (width <= 0 || height <= 0) {
            throw new IllegalArgumentException("Width and height must be positive");
        }
        if (rng == null) {
            throw new NullPointerException("Random source cannot be null");
        }
        
        this.width = width;
        this.height = height;
        this.rng = rng;
        this.score = 0;
        this.gameOver = false;
        
        // Initialize snake at center
        Position start = Position.of(width / 2, height / 2);
        this.snake = new Snake(start);
        this.direction = Direction.UP; // arbitrary initial direction
        
        // Place initial food
        placeFoodRandomly();
    }

    /**
     * Resets the game to its initial state using the same dimensions and random source.
     * This includes resetting the snake, score, and placing food randomly.
     */
    public void reset() {
        // Reinitialize snake at center
        Position start = Position.of(width / 2, height / 2);
        this.snake = new Snake(start);
        this.direction = Direction.UP; // arbitrary initial direction
        this.score = 0;
        this.gameOver = false;
        
        // Place food randomly
        placeFoodRandomly();
    }

    /**
     * Sets the intended movement direction for the snake.
     * This operation is rejected if the requested direction would cause an immediate reversal.
     *
     * @param dir the new direction to set (must not be null)
     * @return true if the direction was accepted, false if it was rejected due to reversal
     * @throws NullPointerException if dir is null
     */
    public boolean setDirection(Direction dir) {
        if (dir == null) {
            throw new NullPointerException("Direction cannot be null");
        }
        
        // Reject immediate reversals
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
     * Moves the snake one cell in the current direction.
     * Handles food consumption, growth, collisions, and score updates.
     *
     * @return the outcome of this tick (MOVED, ATE_FOOD, or GAME_OVER)
     */
    public MoveOutcome tick() {
        if (gameOver) {
            return MoveOutcome.GAME_OVER;
        }
        
        // Calculate next head position based on current direction
        Position currentHead = snake.head();
        Position nextHead = currentHead.plus(direction.dx(), direction.dy());
        
        // Check for collisions (walls or self)
        if (!inBounds(nextHead) || snake.occupies(nextHead)) {
            gameOver = true;
            return MoveOutcome.GAME_OVER;
        }
        
        // Check if food is eaten
        if (nextHead.equals(food)) {
            // Grow snake and increase score
            snake.growTo(nextHead);
            score++;
            
            // Place new food
            placeFoodRandomly();
            
            return MoveOutcome.ATE_FOOD;
        } else {
            // Normal move - just update position
            snake.moveTo(nextHead);
            return MoveOutcome.MOVED;
        }
    }

    /**
     * Checks if the specified position is within the game boundaries.
     *
     * @param p the position to check
     * @return true if the position is within bounds, false otherwise
     */
    private boolean inBounds(Position p) {
        return p.getX() >= 0 && p.getX() < width && p.getY() >= 0 && p.getY() < height;
    }

    /**
     * Places food at a random free position on the grid.
     * If no free positions remain, marks the game as over.
     */
    private void placeFoodRandomly() {
        // Find all free positions
        java.util.List<Position> freePositions = new java.util.ArrayList<>();
        
        for (int x = 0; x < width; x++) {
            for (int y = 0; y < height; y++) {
                Position candidate = Position.of(x, y);
                if (!snake.occupies(candidate)) {
                    freePositions.add(candidate);
                }
            }
        }
        
        // If no free positions, game over
        if (freePositions.isEmpty()) {
            gameOver = true;
            return;
        }
        
        // Choose random free position
        int index = rng.nextInt(freePositions.size());
        this.food = freePositions.get(index);
    }

    /**
     * Determines if the game is currently over.
     *
     * @return true if the game is over, false otherwise
     */
    public boolean isGameOver() {
        return gameOver;
    }

    /**
     * Gets the current score of the player.
     *
     * @return the current score
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
     * Returns an immutable snapshot of the current game state.
     *
     * @return a GameSnapshot representing the current state
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
     * Places food at the specified position deterministically.
     * Validates that the position is within bounds and not occupied by the snake.
     *
     * @param p the position to place food at
     * @throws IllegalArgumentException if p is out of bounds or occupied by the snake
     */
    public void placeFoodAt(Position p) {
        if (p == null) {
            throw new NullPointerException("Food position cannot be null");
        }
        
        if (!inBounds(p)) {
            throw new IllegalArgumentException("Food position is out of bounds");
        }
        
        if (snake.occupies(p)) {
            throw new IllegalArgumentException("Food position is occupied by snake");
        }
        
        this.food = p;
    }
}