/**
 * Runtime entry point for the Caro game.
 * Demonstrates basic functionality with a few safe moves.
 * Prints a concise message and returns normally without System.exit.
 */
public final class Main {
    
    /**
     * Main entry point for the application.
     * Creates a new Game with size 15, performs a couple of safe moves,
     * and prints a message indicating the core is ready.
     * 
     * @param args command line arguments (not used)
     */
    public static void main(String[] args) {
        // Create a new game with a 15x15 board
        Game game = new Game(15);
        
        // Perform a couple of safe moves
        game.placeMove(7, 3);
        game.placeMove(0, 0);
        
        // Print a concise message indicating the core is ready
        System.out.println("Caro core ready");
    }
}