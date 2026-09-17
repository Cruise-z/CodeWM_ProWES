import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Protocol-level tests for the Arkanoid game implementation.
 * These tests verify the core functionality described in the design,
 * including smoke testing, one-brick fixture, and life-loss fixture.
 */
public class MainTest {

    /**
     * Test that the Main.main method executes without throwing any exceptions.
     * This is a basic smoke test to ensure the runtime entry point works.
     */
    @org.junit.jupiter.api.Test
    public void testMainSmoke() {
        assertDoesNotThrow(() -> Main.main(new String[0]), "Main.main should execute without throwing");
    }

    /**
     * Test the one-brick fixture scenario:
     * - A single breakable brick with 1 hit point
     * - Ball collides with the brick, reducing hit points to 0
     * - Brick is removed from the game
     * - Score increases by 100
     * - Level is completed (since there are no more breakable bricks)
     */
    @org.junit.jupiter.api.Test
    public void testOneBrickFixture() {
        // Create a simple game world
        double width = 800.0;
        double height = 600.0;
        
        // Create a paddle centered at the bottom
        double paddleWidth = 100.0;
        double paddleHeight = 10.0;
        Paddle paddle = new Paddle(width / 2, height - 50, paddleWidth, paddleHeight, width);
        
        // Create a ball that will hit the brick
        double ballRadius = 10.0;
        Ball ball = new Ball(400.0, 120.0, 0.0, 100.0, ballRadius); // Moving downward
        
        // Create a single breakable brick at the top center
        Rect brickRect = new Rect(350, 100, 100, 20);
        Brick brick = new Brick(brickRect, 1, true);
        
        // Create the game with one brick
        List<Brick> bricks = Collections.singletonList(brick);
        Game game = new Game(width, height, paddle, ball, bricks, 3);
        
        // Verify initial state
        assertEquals(3, game.getLives(), "Initial lives should be 3");
        assertEquals(0, game.getScore(), "Initial score should be 0");
        assertFalse(game.isLevelCompleted(), "Level should not be completed initially");
        assertFalse(game.isLifeLost(), "No life should be lost initially");
        assertEquals(1, game.getBricks().size(), "There should be 1 brick initially");
        assertTrue(game.getBricks().contains(brick), "The brick should be in the game");
        
        // Run a single tick to hit the brick
        game.tick(0.016); // 60 FPS
        
        // Verify post-tick state
        assertEquals(3, game.getLives(), "Lives should remain 3");
        assertEquals(100, game.getScore(), "Score should be 100 after destroying one brick");
        assertTrue(game.isLevelCompleted(), "Level should be completed after destroying the only brick");
        assertFalse(game.isLifeLost(), "No life should be lost when hitting a brick");
        assertEquals(0, game.getBricks().size(), "There should be no bricks left after destruction");
    }

    /**
     * Test the life-loss fixture scenario:
     * - Ball falls below the bottom of the screen (bottom-out)
     * - Lives should decrement by 1 (from 3 to 2)
     * - LifeLost flag should be set to true
     * - Ball should be reset to paddle position
     * - Ball should have vx=0 and vy = -|previous vy|
     */
    @org.junit.jupiter.api.Test
    public void testLifeLossFixture() {
        // Create a simple game world
        double width = 800.0;
        double height = 600.0;
        
        // Create a paddle centered at the bottom
        double paddleWidth = 100.0;
        double paddleHeight = 10.0;
        Paddle paddle = new Paddle(width / 2, height - 50, paddleWidth, paddleHeight, width);
        
        // Create a ball positioned below the bottom of the screen to trigger bottom-out
        double ballRadius = 10.0;
        Ball ball = new Ball(400.0, 650.0, 100.0, 150.0, ballRadius); // Below the bottom
        
        // Create a single non-breakable brick to ensure level isn't completed
        Rect brickRect = new Rect(350, 100, 100, 20);
        Brick brick = new Brick(brickRect, 1, false); // Non-breakable
        
        // Create the game with one non-breakable brick
        List<Brick> bricks = Collections.singletonList(brick);
        Game game = new Game(width, height, paddle, ball, bricks, 3);
        
        // Verify initial state
        assertEquals(3, game.getLives(), "Initial lives should be 3");
        assertEquals(0, game.getScore(), "Initial score should be 0");
        assertFalse(game.isLevelCompleted(), "Level should not be completed initially");
        assertFalse(game.isLifeLost(), "No life should be lost initially");
        assertEquals(1, game.getBricks().size(), "There should be 1 brick initially");
        
        // Store original velocities for later verification
        double originalVy = ball.getVy();
        
        // Run a single tick that causes bottom-out
        game.tick(0.016); // 60 FPS
        
        // Verify post-tick state
        assertEquals(2, game.getLives(), "Lives should decrement to 2 after bottom-out");
        assertEquals(0, game.getScore(), "Score should remain 0 when life is lost");
        assertFalse(game.isLevelCompleted(), "Level should not be completed when life is lost");
        assertTrue(game.isLifeLost(), "LifeLost flag should be true after bottom-out");
        assertEquals(1, game.getBricks().size(), "There should still be 1 brick after bottom-out");
        
        // Verify ball position and velocity were reset correctly
        assertEquals(paddle.getX(), game.getBall().getX(), 0.001, 
                     "Ball x-position should be reset to paddle center");
        assertEquals(paddle.getY() - paddle.getHeight() / 2 - ballRadius, 
                     game.getBall().getY(), 0.001, 
                     "Ball y-position should be reset above the paddle");
        assertEquals(0.0, game.getBall().getVx(), 0.001, 
                     "Ball x-velocity should be reset to 0");
        assertEquals(-Math.abs(originalVy), game.getBall().getVy(), 0.001, 
                     "Ball y-velocity should be reset to negative absolute of previous vy");
    }
}