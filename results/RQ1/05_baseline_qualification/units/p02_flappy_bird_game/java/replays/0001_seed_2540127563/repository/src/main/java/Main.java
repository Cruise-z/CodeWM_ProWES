/**
 * Main entry point for the Flappy Bird game.
 * Constructs a Game with a seed, performs one standalone tick(),
 * then prints the birdY, birdVy, ticks, score, and pipe count.
 */
public class Main {
    /**
     * Entry point of the application.
     * 
     * @param args command line arguments (not used)
     */
    public static void main(String[] args) {
        // Construct Game with a seed
        Game game = new Game(12345L);
        
        // Perform one standalone tick() call, ignoring its boolean result
        game.tick();
        
        // Print getters in the specified order
        System.out.println(game.birdY());
        System.out.println(game.birdVy());
        System.out.println(game.ticks());
        System.out.println(game.score());
        System.out.println(game.pipes().size());
    }
}