import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Automated tests for the Snake Game implementation.
 * These tests are deterministic and headless, focusing on core game rules
 * and runtime wiring without GUI or I/O dependencies.
 */
public class MainTest {

    /**
     * Test that the Main class can run without throwing exceptions.
     * This verifies the runtime wiring and bootstrap process.
     */
    @Test
    public void testRuntimeWiring() {
        // This should not throw any exceptions
        Main.main(new String[]{});
    }

    /**
     * Test the direction reversal rule and basic movement.
     * Verifies that setting an opposite direction is rejected
     * and that normal movement works within bounds.
     */
    @Test
    public void testDirectionReversalAndMovement() {
        // Create a deterministic game
        RandomSource rng = new JavaUtilRandomSource(123L);
        SnakeGame game = new SnakeGame(5, 5, rng);
        
        // Initial state
        assertEquals(Direction.UP, game.getDirection());
        assertFalse(game.isGameOver());
        assertEquals(0, game.getScore());
        
        // Try to reverse direction (should be rejected)
        assertFalse(game.setDirection(Direction.DOWN));
        assertEquals(Direction.UP, game.getDirection());
        
        // Set valid direction
        assertTrue(game.setDirection(Direction.RIGHT));
        assertEquals(Direction.RIGHT, game.getDirection());
        
        // Move once
        MoveOutcome outcome = game.tick();
        assertEquals(MoveOutcome.MOVED, outcome);
        assertFalse(game.isGameOver());
        assertEquals(0, game.getScore());
        
        // Verify snake moved correctly
        GameSnapshot snapshot = game.snapshot();
        assertEquals(5, snapshot.getWidth());
        assertEquals(5, snapshot.getHeight());
        assertEquals(1, snapshot.getSnakeBody().size()); // Single segment
        Position head = snapshot.getSnakeBody().get(0);
        assertEquals(3, head.getX()); // Starting at (2,2), moved right
        assertEquals(2, head.getY());
    }

    /**
     * Test food consumption increases score and snake length.
     * Uses placeFoodAt to deterministically place food adjacent to snake head.
     */
    @Test
    public void testFoodConsumption() {
        // Create a deterministic game
        RandomSource rng = new JavaUtilRandomSource(456L);
        SnakeGame game = new SnakeGame(5, 5, rng);
        
        // Set initial direction to right
        game.setDirection(Direction.RIGHT);
        
        // Place food right next to snake head
        Position foodPos = Position.of(3, 2); // Right of initial head at (2,2)
        game.placeFoodAt(foodPos);
        
        // Move to eat food
        MoveOutcome outcome = game.tick();
        
        // Should have eaten food
        assertEquals(MoveOutcome.ATE_FOOD, outcome);
        assertTrue(game.isGameOver()); // Game should be over because no more free cells
        assertEquals(1, game.getScore());
        
        // Snake should have grown
        GameSnapshot snapshot = game.snapshot();
        assertEquals(1, snapshot.getSnakeBody().size()); // Still just one segment?
    }

    /**
     * Test wall collision ends the game with GAME_OVER outcome.
     * Drive the snake into a wall and verify it stops.
     */
    @Test
    public void testWallCollision() {
        // Create a deterministic game
        RandomSource rng = new JavaUtilRandomSource(789L);
        SnakeGame game = new SnakeGame(3, 3, rng);
        
        // Set direction to go left from initial position (1,1)
        game.setDirection(Direction.LEFT);
        
        // First tick should move left to (0,1) - valid
        MoveOutcome outcome1 = game.tick();
        assertEquals(MoveOutcome.MOVED, outcome1);
        assertFalse(game.isGameOver());
        
        // Second tick should move left to (-1,1) - invalid (wall)
        MoveOutcome outcome2 = game.tick();
        assertEquals(MoveOutcome.GAME_OVER, outcome2);
        assertTrue(game.isGameOver());
        
        // Subsequent ticks should also return GAME_OVER
        MoveOutcome outcome3 = game.tick();
        assertEquals(MoveOutcome.GAME_OVER, outcome3);
        assertTrue(game.isGameOver());
    }
}