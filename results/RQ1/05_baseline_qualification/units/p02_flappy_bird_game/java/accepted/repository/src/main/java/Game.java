/**
 * Orchestrates the Flappy Bird game state, managing the bird, pipes, scoring,
 * and game loop logic according to the specified rules.
 */
public class Game {
    /** The width of the game world */
    private final double worldWidth;
    
    /** The height of the game world */
    private final double worldHeight;
    
    /** The interval at which pipes are spawned */
    private final int spawnInterval;
    
    /** The fixed X position of the bird for collision and scoring */
    private final double birdX;
    
    /** The bird object representing the player */
    private Bird bird;
    
    /** List of active pipes in the game */
    private java.util.List<PipePair> pipes;
    
    /** Counter for the number of ticks elapsed */
    private long tickCount;
    
    /** Current score of the player */
    private int score;
    
    /** Current state of the game (RUNNING or GAME_OVER) */
    private GameState state;
    
    /** Random number generator for pipe placement */
    private RNG rng;

    /**
     * Creates a new game with the specified seed.
     * Delegates to Game(seed, 400.0, 600.0, 100).
     *
     * @param seed the seed for random number generation
     */
    public Game(long seed) {
        this(seed, 400.0, 600.0, 100);
    }

    /**
     * Creates a new game with the specified parameters.
     *
     * @param seed the seed for random number generation
     * @param worldWidth the width of the game world
     * @param worldHeight the height of the game world
     * @param spawnInterval the interval at which pipes are spawned
     */
    public Game(long seed, double worldWidth, double worldHeight, int spawnInterval) {
        this.worldWidth = worldWidth;
        this.worldHeight = worldHeight;
        this.spawnInterval = spawnInterval;
        this.birdX = 100.0; // Fixed bird X position as per specification
        
        reset(seed);
    }

    /**
     * Executes one tick of the game logic.
     * Returns false if the game is over, true otherwise.
     *
     * @return true if the game is still running, false if game over
     */
    public boolean tick() {
        // If game is over, do nothing
        if (state == GameState.GAME_OVER) {
            return false;
        }
        
        // Apply physics to the bird
        bird.applyGravity();
        bird.integrate();
        
        // Check for collisions with boundaries
        if (CollisionDetector.hitBounds(bird, 30.0, worldHeight)) {
            state = GameState.GAME_OVER;
            return false;
        }
        
        // Check for collisions with pipes
        for (PipePair pipe : pipes) {
            if (CollisionDetector.hitPipe(bird, 30.0, 30.0, pipe, worldHeight)) {
                state = GameState.GAME_OVER;
                return false;
            }
        }
        
        // Check for scoring
        for (PipePair pipe : pipes) {
            if (ScoreSystem.passedPipe(birdX, pipe)) {
                score++;
            }
        }
        
        // Increment tick count
        tickCount++;
        
        // Spawn new pipes if needed
        if (tickCount % spawnInterval == 0) {
            spawnPipe();
        }
        
        // Move all pipes
        for (PipePair pipe : pipes) {
            pipe.move();
        }
        
        // Remove off-screen pipes
        pipes.removeIf(pipe -> pipe.x() + pipe.width() < 0);
        
        return true;
    }

    /**
     * Resets the game state with a new seed.
     *
     * @param seed the new seed for random number generation
     */
    public void reset(long seed) {
        // Reset game state
        state = GameState.RUNNING;
        
        // Initialize RNG with new seed
        rng = new RNG(seed);
        
        // Reset game elements
        tickCount = 0;
        score = 0;
        pipes = new java.util.ArrayList<>();
        
        // Initialize bird at center of screen with zero velocity
        bird = new Bird(worldHeight / 2.0);
    }

    /**
     * Makes the bird flap if the game is running.
     */
    public void flapBird() {
        if (state == GameState.RUNNING) {
            bird.flap();
        }
    }

    /**
     * Gets the current Y position of the bird.
     *
     * @return the Y position of the bird
     */
    public double birdY() {
        return bird.y();
    }

    /**
     * Gets the current Y velocity of the bird.
     *
     * @return the Y velocity of the bird
     */
    public double birdVy() {
        return bird.vy();
    }

    /**
     * Gets the current tick count.
     *
     * @return the number of ticks elapsed
     */
    public long ticks() {
        return tickCount;
    }

    /**
     * Gets the current score.
     *
     * @return the current score
     */
    public int score() {
        return score;
    }

    /**
     * Gets the list of pipes.
     *
     * @return the list of active pipes
     */
    public java.util.List<PipePair> pipes() {
        return pipes;
    }
    
    /**
     * Spawns a new pipe at the right side of the screen.
     */
    private void spawnPipe() {
        // Generate random gap position
        double gapY = rng.nextDouble() * (worldHeight - 100) + 50;
        double gapHeight = 150.0; // Fixed gap height
        
        // Create new pipe pair
        PipePair pipe = new PipePair(
            worldWidth,   // Start at right edge of screen
            50.0,         // Fixed pipe width
            gapY,         // Gap top position
            gapHeight,    // Gap height
            3.0           // Fixed speed
        );
        
        pipes.add(pipe);
    }
}