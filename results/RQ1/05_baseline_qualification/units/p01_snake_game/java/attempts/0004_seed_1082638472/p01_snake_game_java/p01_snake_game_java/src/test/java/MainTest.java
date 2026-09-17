import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Automated tests for the Snake Game implementation.
 * These tests are deterministic and headless, covering:
 * 1. Runtime wiring via Main.main executes without exception
 * 2. Direction reversal rule and basic movement
 * 3. Food consumption causes growth and score increment
 * 4. Wall collision ends the game with GAME_OVER
 */
public class MainTest {

    /**
     * Test that Main.main runs without throwing any exceptions.
     * This verifies the runtime wiring and bootstrap functionality.
     */
    @Test
    public void testRuntimeWiring() {
        // This should not throw any exceptions
        Main.main(new String[0]);
    }

    /**
     * Test that the direction reversal rule works correctly.
     * Setting the opposite direction should be rejected.
     */
    @Test
    public void testDirectionReversalRule() {
        // Create a game with a small grid and deterministic RNG
        RandomSource rng = new JavaUtilRandomSource(42L);
        SnakeGame game = new SnakeGame(5, 5, rng);

        // Initial direction should be UP
        assertEquals(Direction.UP, game.getDirection());

        // Try to set opposite direction (DOWN) - should be rejected
        assertFalse(game.setDirection(Direction.DOWN));
        // Direction should remain unchanged
        assertEquals(Direction.UP, game.getDirection());

        // Try to set a valid direction (RIGHT) - should be accepted
        assertTrue(game.setDirection(Direction.RIGHT));
        // Direction should now be RIGHT
        assertEquals(Direction.RIGHT, game.getDirection());
    }

    /**
     * Test that food consumption works correctly.
     * Placing food adjacent to the snake head should result in growth and score increase.
     */
    @Test
    public void testFoodConsumption() {
        // Create a game with a small grid and deterministic RNG
        RandomSource rng = new JavaUtilRandomSource(42L);
        SnakeGame game = new SnakeGame(5, 5, rng);

        // Get initial state
        int initialLength = game.snapshot().getSnakeBody().size();
        int initialScore = game.getScore();

        // Place food directly adjacent to the snake head (to the right)
        Position foodPosition = game.snapshot().getSnakeBody().get(0).plus(1, 0);
        game.placeFoodAt(foodPosition);

        // Set direction to move right to eat the food
        game.setDirection(Direction.RIGHT);

        // Tick to consume the food
        MoveOutcome outcome = game.tick();

        // Verify the outcome
        assertEquals(MoveOutcome.ATE_FOOD, outcome);

        // Verify that the snake grew (length increased)
        assertEquals(initialLength + 1, game.snapshot().getSnakeBody().size());

        // Verify that the score increased
        assertEquals(initialScore + 1, game.getScore());
    }

    /**
     * Test that wall collision properly ends the game.
     * Moving the snake into a wall should result in GAME_OVER.
     */
    @Test
    public void testWallCollision() {
        // Create a small game grid (3x3) with deterministic RNG
        RandomSource rng = new JavaUtilRandomSource(42L);
        SnakeGame game = new SnakeGame(3, 3, rng);

        // Place food at a position that forces wall collision
        // Start at center (1,1), then move to edge (0,1) and try to go left to wall
        game.placeFoodAt(Position.of(2, 1)); // Place food on the right side

        // Set direction to move left from (1,1) to (0,1) - valid move
        game.setDirection(Direction.LEFT);
        MoveOutcome outcome = game.tick();
        assertEquals(MoveOutcome.MOVED, outcome);

        // Now set direction to move left again from (0,1) to (-1,1) - this is a wall collision
        game.setDirection(Direction.LEFT);
        outcome = game.tick();

        // Should result in GAME_OVER
        assertEquals(MoveOutcome.GAME_OVER, outcome);

        // Game should be marked as over
        assertTrue(game.isGameOver());
    }
}