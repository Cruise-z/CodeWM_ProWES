import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Protocol-level tests for the Flappy Bird core implementation.
 * Covers physics fixture, reset+flap behavior, RNG paired streams,
 * and scoring strictness with handcrafted PipePair.
 */
public class MainTest {

    /**
     * Test physics fixture: Game(12345L) initial state and one tick
     * should result in vy=0.5 and y=300.5 (worldHeight/2 + 0.5).
     */
    @Test
    public void testPhysicsFixture() {
        Game game = new Game(12345L);
        
        // Initial state check
        assertEquals(300.0, game.birdY(), 0.0, "Initial bird Y should be worldHeight/2");
        assertEquals(0.0, game.birdVy(), 0.0, "Initial bird Vy should be 0.0");
        
        // After one tick: applyGravity() then integrate()
        // vy = 0.0 + 0.5 = 0.5 (clamped to [-10,10])
        // y = 300.0 + 0.5 = 300.5
        game.tick();
        
        assertEquals(0.5, game.birdVy(), 0.0, "After one tick, bird Vy should be 0.5");
        assertEquals(300.5, game.birdY(), 0.0, "After one tick, bird Y should be 300.5");
    }

    /**
     * Test reset and flap fixture: after reset(12345L), flapBird(), then one tick
     * should give vy=-7.5 and y=292.5.
     */
    @Test
    public void testResetAndFlapFixture() {
        Game game = new Game(12345L);
        
        // Reset with same seed
        game.reset(12345L);
        
        // Flap the bird
        game.flapBird();
        
        // After flap: vy should become -8.0
        assertEquals(-8.0, game.birdVy(), 0.0, "After flap, bird Vy should be -8.0");
        
        // Take one tick: applyGravity() then integrate()
        // vy = -8.0 + 0.5 = -7.5 (clamped to [-10,10])
        // y = 300.0 + (-7.5) = 292.5
        game.tick();
        
        assertEquals(-7.5, game.birdVy(), 0.0, "After flap and one tick, bird Vy should be -7.5");
        assertEquals(292.5, game.birdY(), 0.0, "After flap and one tick, bird Y should be 292.5");
    }

    /**
     * Test RNG paired streams fixture: identical nextDouble and nextInt(100)
     * after double seed() call from two RNG instances with same seed.
     */
    @Test
    public void testRNGPairedStreamsFixture() {
        RNG a = new RNG(98765L);
        RNG b = new RNG(98765L);
        
        // Verify both have the same original seed
        assertEquals(98765L, a.seed(), "RNG a seed should be 98765L");
        assertEquals(98765L, b.seed(), "RNG b seed should be 98765L");
        
        // Verify they produce identical values when consuming
        assertEquals(a.nextDouble(), b.nextDouble(), 0.0, "Next doubles should be equal");
        assertEquals(a.nextInt(100), b.nextInt(100), "Next ints should be equal");
        
        // Consume more values to ensure consistency
        assertEquals(a.nextDouble(), b.nextDouble(), 0.0, "Next doubles should still be equal");
        assertEquals(a.nextInt(100), b.nextInt(100), "Next ints should still be equal");
    }

    /**
     * Test scoring strictness: with handcrafted PipePair(100.0,50.0,100.0,150.0,3.0),
     * verify ScoreSystem.passedPipe(birdX, pipe) triggers only when
     * pipe.x()+pipe.width() < birdX and marks scored exactly once.
     */
    @Test
    public void testScoringStrictnessFixture() {
        // Create a handcrafted pipe pair with x=100.0, width=50.0, gapY=100.0, gapHeight=150.0, speed=3.0
        PipePair pipe = new PipePair(100.0, 50.0, 100.0, 150.0, 3.0);
        
        // Bird X position used by Game for scoring (from Game constructor)
        double birdX = 100.0;
        
        // Initially pipe should not be scored
        assertFalse(pipe.scored(), "Pipe should initially not be scored");
        
        // Test case 1: bird at x=149.9 (pipe trailing edge at 150.0) - should NOT trigger scoring
        // Because 150.0 is NOT < 149.9
        assertFalse(ScoreSystem.passedPipe(149.9, pipe), "Should not score when trailing edge >= birdX");
        assertFalse(pipe.scored(), "Pipe should remain unscored");
        
        // Test case 2: bird at x=150.1 (pipe trailing edge at 150.0) - SHOULD trigger scoring
        // Because 150.0 < 150.1
        assertTrue(ScoreSystem.passedPipe(150.1, pipe), "Should score when trailing edge < birdX");
        assertTrue(pipe.scored(), "Pipe should now be marked scored");
        
        // Test case 3: subsequent calls should NOT trigger scoring even if bird moves back
        assertFalse(ScoreSystem.passedPipe(140.0, pipe), "Should not score again after pipe is already scored");
        assertTrue(pipe.scored(), "Pipe should remain scored");
    }
}