/**
 * Main entry point for the Snake Game demonstration.
 * This class provides a non-interactive console-based demo
 * showing the game mechanics in action.
 */
public final class Main {
    
    /**
     * Entry point of the application.
     * Constructs a game with a fixed seed for deterministic behavior,
     * runs a few ticks, and prints snapshots of the game state.
     *
     * @param args command-line arguments (unused)
     */
    public static void main(String[] args) {
        try {
            // Create a deterministic random source with a fixed seed
            RandomSource rng = new JavaUtilRandomSource(42L);
            
            // Create a game with a small 10x10 grid
            SnakeGame game = new SnakeGame(10, 10, rng);
            
            // Print initial state
            System.out.println("Initial state:");
            System.out.println(game.snapshot());
            
            // Perform a few deterministic ticks
            System.out.println("\nTick 1:");
            MoveOutcome outcome1 = game.tick();
            System.out.println("Outcome: " + outcome1);
            System.out.println(game.snapshot());
            
            System.out.println("\nTick 2:");
            MoveOutcome outcome2 = game.tick();
            System.out.println("Outcome: " + outcome2);
            System.out.println(game.snapshot());
            
            System.out.println("\nFinal state:");
            System.out.println(game.snapshot());
            
        } catch (Exception e) {
            // Print any unexpected exception and exit normally
            System.err.println("Error during execution: " + e.getMessage());
        }
    }
}