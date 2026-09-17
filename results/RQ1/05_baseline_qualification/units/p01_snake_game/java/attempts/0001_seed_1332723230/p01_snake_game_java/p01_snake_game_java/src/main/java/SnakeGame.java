import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * Core game engine managing movement, reversal rule, growth, collisions, scoring, and food placement.
 * This class orchestrates all game rules and provides a canonical API for external consumers.
 */
public final class SnakeGame {
    /** The width of the game grid. */
    private final int width;
    
    /** The height of the game grid. */
    private final int height;
    
    /** The snake object representing the player's snake. */
    private Snake snake;
    
    /** Random number generator for placing food. */
    private final RandomSource rng;
    
    /** Current movement direction of the snake. */
    private Direction direction;
    
    /** Position of the current food item. */
    private Position food;
    
    /** Current score of the player. */
    private int score;
    
    /** Flag indicating whether the game is over. */
    private boolean gameOver;

    /**
     * Constructs a new SnakeGame with the specified dimensions and random source.
     * Initializes the snake at a valid starting position, score to 0, and places food randomly.
     *
     * @param width the width of the game grid (> 0)
     * @param height the height of the game grid (> 0)
     * @param rng the random source for food placement
     * @throws IllegalArgumentException if width or height is not positive
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
        
        // Initialize snake at a fixed starting position (middle of grid)
        Position start = Position.of(width / 2, height / 2);
        this.snake = new Snake(start);
        this.direction = Direction.UP; // Default direction
        
        // Place initial food
        placeFoodRandomly();
    }

    /**
     * Resets the game to its initial state with the same dimensions and random source.
     * The snake is reset to a single segment at the center, score is zero, and food is placed randomly.
     */
    public void reset() {
        // Reset game state
        this.score = 0;
        this.gameOver = false;
        
        // Reinitialize snake at center
        Position start = Position.of(width / 2, height / 2);
        this.snake = new Snake(start);
        this.direction = Direction.UP;
        
        // Place food randomly
        placeFoodRandomly();
    }

    /**
     * Attempts to set the snake's movement direction.
     * Rejects immediate reversals to prevent the snake from turning into itself.
     *
     * @param dir the desired direction to move
     * @return true if the direction was successfully set, false if it was rejected due to reversal
     */
    public boolean setDirection(Direction dir) {
        if (dir == null) {
            return false;
        }
        
        // Prevent immediate reversal
        if (direction.isOpposite(dir)) {
            return false;
        }
        
        this.direction = dir;
        return true;
    }

    /**
     * Returns the current movement direction of the snake.
     *
     * @return the current direction
     */
    public Direction getDirection() {
        return direction;
    }

    /**
     * Advances the game state by one tick.
     * Moves the snake one cell in its current direction.
     * Handles food consumption, growth, collisions, and scoring.
     *
     * @return the outcome of this tick (MOVED, ATE_FOOD, or GAME_OVER)
     */
    public MoveOutcome tick() {
        if (gameOver) {
            return MoveOutcome.GAME_OVER;
        }
        
        // Calculate next head position
        Position currentHead = snake.head();
        Position nextHead = currentHead.plus(direction.dx(), direction.dy());
        
        // Check for boundary collision
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
        snake.moveTo(nextHead);
        
        // Check if snake ate food
        if (nextHead.equals(food)) {
            // Snake grows by not removing tail
            snake.growTo(nextHead);
            
            // Increment score
            score++;
            
            // Place new food
            placeFoodRandomly();
            
            return MoveOutcome.ATE_FOOD;
        }
        
        // Normal movement
        return MoveOutcome.MOVED;
    }

    /**
     * Checks if a position is within the game grid boundaries.
     *
     * @param p the position to check
     * @return true if the position is within bounds, false otherwise
     */
    private boolean inBounds(Position p) {
        return p.getX() >= 0 && p.getX() < width && p.getY() >= 0 && p.getY() < height;
    }

    /**
     * Places food at a random free cell on the grid.
     * If no free cells are available, sets game over.
     */
    private void placeFoodRandomly() {
        // Find all free cells
        List<Position> freeCells = new ArrayList<>();
        for (int x = 0; x < width; x++) {
            for (int y = 0; y < height; y++) {
                Position pos = Position.of(x, y);
                if (!snake.occupies(pos)) {
                    freeCells.add(pos);
                }
            }
        }
        
        // Check if there are any free cells
        if (freeCells.isEmpty()) {
            gameOver = true;
            return;
        }
        
        // Choose random free cell
        int index = rng.nextInt(freeCells.size());
        this.food = freeCells.get(index);
    }

    /**
     * Returns whether the game is currently over.
     *
     * @return true if the game is over, false otherwise
     */
    public boolean isGameOver() {
        return gameOver;
    }

    /**
     * Returns the current score of the player.
     *
     * @return the score
     */
    public int getScore() {
        return score;
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
     * Places food at a specific position.
     * Validates that the position is within bounds and not occupied by the snake.
     *
     * @param p the position to place the food
     * @throws IllegalArgumentException if position is out of bounds or occupied
     */
    public void placeFoodAt(Position p) {
        if (p == null) {
            throw new NullPointerException("Food position cannot be null");
        }
        
        if (!inBounds(p)) {
            throw new IllegalArgumentException("Food position must be within grid bounds");
        }
        
        if (snake.occupies(p)) {
            throw new IllegalArgumentException("Food cannot be placed on snake body");
        }
        
        this.food = p;
    }
}