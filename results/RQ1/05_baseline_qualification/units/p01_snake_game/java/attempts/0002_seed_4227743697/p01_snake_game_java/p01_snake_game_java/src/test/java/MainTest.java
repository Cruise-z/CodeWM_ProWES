import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Automated tests for the Snake Game implementation.
 * These tests are deterministic and headless, focusing on
 * runtime wiring and core game rules.
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
     * Verifies that setting the opposite direction is rejected,
     * and that normal movement works correctly.
     */
    @Test
    public void testDirectionReversalAndMovement() {
        // Create a game with a small grid and deterministic RNG
        RandomSource rng = new JavaUtilRandomSource(123L);
        SnakeGame game = new SnakeGame(5, 5, rng);
        
        // Initial direction should be UP
        assertEquals(Direction.UP, game.getDirection());
        
        // Try to reverse direction (should be rejected)
        assertFalse(game.setDirection(Direction.DOWN));
        // Direction should remain unchanged
        assertEquals(Direction.UP, game.getDirection());
        
        // Set a valid direction (should be accepted)
        assertTrue(game.setDirection(Direction.RIGHT));
        assertEquals(Direction.RIGHT, game.getDirection());
        
        // Move one step
        MoveOutcome outcome = game.tick();
        assertEquals(MoveOutcome.MOVED, outcome);
        
        // Verify the snake has moved right
        GameSnapshot snapshot = game.snapshot();
        assertEquals(1, snapshot.getSnakeBody().get(0).getX()); // Head moved right
        assertEquals(2, snapshot.getSnakeBody().get(0).getY()); // Head at initial Y
    }

    /**
     * Test food consumption causes growth and score increment.
     * Places food adjacent to the snake's head and verifies
     * the snake grows and score increases.
     */
    @Test
    public void testFoodConsumption() {
        // Create a game with a small grid and deterministic RNG
        RandomSource rng = new JavaUtilRandomSource(456L);
        SnakeGame game = new SnakeGame(5, 5, rng);
        
        // Set direction to move towards food
        game.setDirection(Direction.RIGHT);
        
        // Place food directly to the right of the snake's head
        Position foodPos = new Position(3, 2); // Snake starts at (2,2)
        game.placeFoodAt(foodPos);
        
        // Move the snake to eat the food
        MoveOutcome outcome = game.tick();
        
        // Should have eaten the food
        assertEquals(MoveOutcome.ATE_FOOD, outcome);
        
        // Score should have increased
        assertEquals(1, game.getScore());
        
        // Snake should have grown (length increased)
        assertEquals(2, game.snapshot().getSnakeBody().size());
        
        // Food should be placed elsewhere (different position)
        assertNotEquals(foodPos, game.snapshot().getFood());
    }

    /**
     * Test that wall collision ends the game with GAME_OVER outcome.
     * Drives the snake into a wall and verifies the game ends properly.
     */
    @Test
    public void testWallCollision() {
        // Create a small game grid
        RandomSource rng = new JavaUtilRandomSource(789L);
        SnakeGame game = new SnakeGame(3, 3, rng);
        
        // Set direction to move towards the wall
        game.setDirection(Direction.LEFT); // Snake starts at (1,1), left goes to (0,1)
        
        // Make several moves to reach the wall
        for (int i = 0; i < 2; i++) {
            MoveOutcome outcome = game.tick();
            // All moves should succeed until we hit the wall
            assertFalse(game.isGameOver());
        }
        
        // Now move into the wall (left from (0,1) goes to (-1,1))
        MoveOutcome outcome = game.tick();
        
        // Game should now be over
        assertTrue(game.isGameOver());
        assertEquals(MoveOutcome.GAME_OVER, outcome);
        
        // Should not be able to move further
        MoveOutcome outcome2 = game.tick();
        assertEquals(MoveOutcome.GAME_OVER, outcome2);
    }
}