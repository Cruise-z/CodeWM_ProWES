import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Automated tests for the Snake Game implementation.
 * These tests are deterministic and headless, focusing on core game rules
 * and runtime wiring without GUI or I/O dependencies.
 */
public class MainTest {

    /**
     * Test that the runtime entry point Main.main executes without throwing
     * any exceptions and returns promptly (non-interactive).
     */
    @Test
    public void testRuntimeWiring() {
        // This test ensures Main.main runs without exceptions
        // and doesn't get stuck in loops or require interaction
        assertDoesNotThrow(() -> Main.main(new String[0]));
    }

    /**
     * Test the direction reversal rule and basic movement.
     * Verifies that setting the opposite direction is rejected,
     * and normal movement proceeds correctly within bounds.
     */
    @Test
    public void testDirectionReversalAndMovement() {
        // Create a deterministic game
        RandomSource rng = new JavaUtilRandomSource(123L);
        SnakeGame game = new SnakeGame(5, 5, rng);
        
        // Verify initial direction is UP
        assertEquals(Direction.UP, game.getDirection());
        
        // Try to reverse direction (should be rejected)
        assertFalse(game.setDirection(Direction.DOWN));
        // Direction should remain unchanged
        assertEquals(Direction.UP, game.getDirection());
        
        // Set a valid direction
        assertTrue(game.setDirection(Direction.RIGHT));
        assertEquals(Direction.RIGHT, game.getDirection());
        
        // Perform a move - should succeed
        MoveOutcome outcome = game.tick();
        assertEquals(MoveOutcome.MOVED, outcome);
        
        // Verify the snake moved right
        GameSnapshot snapshot = game.snapshot();
        Position head = snapshot.getSnakeBody().get(0); // Head is first element
        assertEquals(1, head.getX()); // Moved from 0 to 1
        assertEquals(2, head.getY()); // Y stays same (initial at 2)
    }

    /**
     * Test food consumption increases score and snake length.
     * Uses placeFoodAt to deterministically position food adjacent to snake head
     * and verifies the growth and scoring behavior.
     */
    @Test
    public void testFoodConsumption() {
        // Create a deterministic game
        RandomSource rng = new JavaUtilRandomSource(456L);
        SnakeGame game = new SnakeGame(5, 5, rng);
        
        // Reset to known state
        game.reset();
        
        // Place food directly adjacent to snake head (right side)
        Position foodPos = new Position(1, 2); // Snake starts at (0,2)
        game.placeFoodAt(foodPos);
        
        // Set direction to move right
        game.setDirection(Direction.RIGHT);
        
        // Tick - should eat food
        MoveOutcome outcome = game.tick();
        assertEquals(MoveOutcome.ATE_FOOD, outcome);
        
        // Score should increase by 1
        assertEquals(1, game.getScore());
        
        // Snake should have grown (length increased by 1)
        GameSnapshot snapshot = game.snapshot();
        assertEquals(2, snapshot.getSnakeBody().size()); // Original + 1
        
        // New head should be at food position
        Position newHead = snapshot.getSnakeBody().get(0);
        assertEquals(foodPos, newHead);
    }

    /**
     * Test wall collision ends the game with GAME_OVER outcome.
     * Moves snake towards a wall and verifies the game state changes accordingly.
     */
    @Test
    public void testWallCollision() {
        // Create a deterministic game
        RandomSource rng = new JavaUtilRandomSource(789L);
        SnakeGame game = new SnakeGame(3, 3, rng);
        
        // Reset to known state
        game.reset();
        
        // Set direction to move left from starting position (1,1)
        game.setDirection(Direction.LEFT);
        
        // Move left twice to hit wall
        game.tick(); // First move - should be OK
        MoveOutcome outcome = game.tick(); // Second move - should collide with wall
        
        assertEquals(MoveOutcome.GAME_OVER, outcome);
        assertTrue(game.isGameOver());
        
        // Game should remain over
        MoveOutcome finalOutcome = game.tick();
        assertEquals(MoveOutcome.GAME_OVER, finalOutcome);
        assertTrue(game.isGameOver());
    }
}