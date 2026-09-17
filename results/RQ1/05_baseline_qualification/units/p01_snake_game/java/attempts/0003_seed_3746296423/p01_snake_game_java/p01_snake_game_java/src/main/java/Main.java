/**
 * Main entry point for the Snake Game demonstration.
 * This class demonstrates the core functionality of the SnakeGame
 * with a fixed seed for deterministic behavior.
 */
public final class Main {
    
    /**
     * Entry point of the application.
     * Creates a SnakeGame with a small grid, prints initial state,
     * performs several deterministic ticks, and prints final state.
     * 
     * @param args command-line arguments (not used)
     */
    public static void main(String[] args) {
        try {
            // Create a deterministic random source with a fixed seed
            RandomSource rng = new JavaUtilRandomSource(42L);
            
            // Create a new SnakeGame with a 10x10 grid
            SnakeGame game = new SnakeGame(10, 10, rng);
            
            // Print initial game state
            System.out.println("Initial state:");
            System.out.println(game.snapshot());
            
            // Perform a few deterministic ticks
            System.out.println("\nRunning ticks:");
            
            // Tick 1: Move Down
            MoveOutcome outcome1 = game.tick();
            System.out.printf("Tick 1 - Outcome: %s%n", outcome1);
            System.out.println(game.snapshot());
            
            // Tick 2: Move Down
            MoveOutcome outcome2 = game.tick();
            System.out.printf("Tick 2 - Outcome: %s%n", outcome2);
            System.out.println(game.snapshot());
            
            // Tick 3: Move Right
            boolean dirSet = game.setDirection(Direction.RIGHT);
            if (dirSet) {
                MoveOutcome outcome3 = game.tick();
                System.out.printf("Tick 3 - Outcome: %s%n", outcome3);
                System.out.println(game.snapshot());
            }
            
            // Print final game state
            System.out.println("\nFinal state:");
            System.out.println(game.snapshot());
            
        } catch (Exception e) {
            // Print error message and exit normally
            System.err.println("Error during execution: " + e.getMessage());
        }
    }
}