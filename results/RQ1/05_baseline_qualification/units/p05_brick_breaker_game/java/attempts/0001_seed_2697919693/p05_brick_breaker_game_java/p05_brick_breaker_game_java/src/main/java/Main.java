/**
 * Main entry point for the Arkanoid game demonstration.
 * Creates a minimal game state and prints a status line.
 */
public final class Main {
    /**
     * Entry point of the application.
     * Creates a simple game with a paddle, ball, and one brick,
     * runs a single tick, and prints the resulting state.
     *
     * @param args command-line arguments (unused)
     */
    public static void main(String[] args) {
        // Create a simple game world
        double width = 800.0;
        double height = 600.0;
        
        // Create a paddle centered at the bottom
        double paddleWidth = 100.0;
        double paddleHeight = 10.0;
        Paddle paddle = new Paddle(width / 2, height - 50, paddleWidth, paddleHeight, width);
        
        // Create a ball above the paddle
        double ballRadius = 10.0;
        Ball ball = new Ball(width / 2, height - 100, 100.0, -150.0, ballRadius);
        
        // Create a single breakable brick
        Rect brickRect = new Rect(350, 100, 100, 20);
        Brick brick = new Brick(brickRect, 1, true);
        
        // Create the game with one brick
        java.util.List<Brick> bricks = java.util.Arrays.asList(brick);
        Game game = new Game(width, height, paddle, ball, bricks, 3);
        
        // Run a single tick
        game.tick(0.016); // 60 FPS
        
        // Print status line
        System.out.printf("Lives: %d, Score: %d, Level Completed: %b%n", 
                         game.getLives(), 
                         game.getScore(), 
                         game.isLevelCompleted());
    }
}