/**
 * Entry point for the Snake Game demonstration.
 * This class provides a minimal, non-interactive console-based demo
 * of the game mechanics using a fixed seed for deterministic behavior.
 */
public final class Main {
    /**
     * Main method serves as the runtime entry point.
     * Demonstrates game initialization, a few deterministic ticks,
     * and final game state printing.
     *
     * @param args command-line arguments (ignored)
     */
    public static void main(String[] args) {
        try {
            // Create a deterministic random source with a fixed seed
            final RandomSource rng = new JavaUtilRandomSource(42L);
            
            // Initialize the game with a small grid
            final SnakeGame game = new SnakeGame(10, 10, rng);
            
            // Print initial game state
            System.out.println("Initial state:");
            System.out.println(game.snapshot());
            
            // Perform a few deterministic ticks
            System.out.println("\nGameplay:");
            MoveOutcome outcome = game.tick();
            System.out.printf("Tick result: %s%n", outcome);
            System.out.println("State after tick:");
            System.out.println(game.snapshot());
            
            // Change direction and tick again
            game.setDirection(Direction.RIGHT);
            outcome = game.tick();
            System.out.printf("Tick result: %s%n", outcome);
            System.out.println("State after tick:");
            System.out.println(game.snapshot());
            
            // Continue with more ticks
            game.setDirection(Direction.DOWN);
            outcome = game.tick();
            System.out.printf("Tick result: %s%n", outcome);
            System.out.println("State after tick:");
            System.out.println(game.snapshot());
            
            // Final state
            System.out.println("\nFinal state:");
            System.out.println(game.snapshot());
            
        } catch (Exception e) {
            // Handle any unexpected exceptions gracefully
            System.err.println("Error during execution: " + e.getMessage());
        }
    }
}