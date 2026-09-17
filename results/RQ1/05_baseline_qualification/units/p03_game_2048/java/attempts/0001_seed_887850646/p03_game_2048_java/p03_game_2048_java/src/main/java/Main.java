/**
 * Main class for running a deterministic headless demo of the 2048 game.
 * This class demonstrates the core functionality by initializing a game,
 * performing one move, and printing the resulting state to the console.
 */
public final class Main {
    /**
     * Entry point for the application.
     * Constructs a deterministic SequenceSpawner, Board, and Game.
     * Resets the game, performs one move (LEFT), and prints the grid, score, and status.
     *
     * @param args command-line arguments (not used)
     */
    public static void main(String[] args) {
        // Create a deterministic spawner with a documented sequence
        SequenceSpawner spawner = SequenceSpawner.defaultSequence();
        
        // Create the game board
        Board board = new Board();
        
        // Create the game with the board and spawner
        Game game = new Game(board, spawner);
        
        // Reset the game to initial state
        game.reset();
        
        // Perform one move to the left
        game.move(Direction.LEFT);
        
        // Print the current state
        printGameState(game);
    }
    
    /**
     * Prints the current game state including the grid, score, and status.
     *
     * @param game the game instance to print
     */
    private static void printGameState(Game game) {
        // Get a deep copy of the grid to avoid modifying the original
        int[][] grid = game.getGridCopy();
        
        // Print the grid
        for (int[] row : grid) {
            for (int cell : row) {
                System.out.printf("%4d ", cell);
            }
            System.out.println();
        }
        
        // Print score and status
        System.out.println("Score: " + game.getScore());
        System.out.println("Status: " + game.getStatus());
    }
}