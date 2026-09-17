/**
 * Main entry point for the Snake Game demonstration.
 * This class provides a minimal, non-interactive console-based demo
 * of the game mechanics using a fixed seed for deterministic behavior.
 */
public final class Main {
    /**
     * Entry point of the application.
     * Creates a game with fixed parameters, runs a few deterministic ticks,
     * and prints the game state at each step.
     *
     * @param args command-line arguments (ignored)
     */
    public static void main(String[] args) {
        try {
            // Create a deterministic random source with a fixed seed
            final RandomSource rng = new JavaUtilRandomSource(42L);
            
            // Create a game with a small grid
            final SnakeGame game = new SnakeGame(10, 10, rng);
            
            // Print initial state
            System.out.println("Initial state:");
            System.out.println(game.snapshot());
            
            // Perform a few deterministic ticks
            System.out.println("\nTicks:");
            for (int i = 0; i < 5; i++) {
                MoveOutcome outcome = game.tick();
                System.out.printf("Tick %d: %s%n", i + 1, outcome);
                System.out.println(game.snapshot());
            }
            
            // Print final state
            System.out.println("\nFinal state:");
            System.out.println(game.snapshot());
        } catch (Exception e) {
            // Handle any unexpected errors gracefully
            System.err.println("Error during game execution: " + e.getMessage());
        }
    }
}