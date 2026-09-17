import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

import java.util.*;

public class MainTest {

    @Test
    public void testMainReturnsNormally() {
        // Just verify that Main.main runs without throwing exceptions
        assertDoesNotThrow(() -> Main.main(new String[0]));
    }

    @Test
    public void testBlockedMovementTurnAndReset() {
        // Setup: Arena(6,5) with obstacle at (2,2)
        // Alice at (1,2) EAST health3
        // Bob at (4,2) WEST health3
        
        ObstacleMap obstacles = ObstacleMap.empty();
        obstacles.add(new Position(2, 2));
        Arena arena = new Arena(6, 5, obstacles);
        
        Tank alice = new Tank("Alice", new Position(1, 2), Orientation.EAST, 3);
        Tank bob = new Tank("Bob", new Position(4, 2), Orientation.WEST, 3);
        
        GameEngine engine = new GameEngine(arena, Arrays.asList(alice, bob));
        
        // Verify Alice starts at (1,2) EAST
        Tank aliceCopy = engine.getTanksCopy().get("Alice");
        assertEquals(new Position(1, 2), aliceCopy.getPosition());
        assertEquals(Orientation.EAST, aliceCopy.getOrientation());
        assertEquals(3, aliceCopy.getHealth());
        
        // Try to move Alice forward - should be blocked by obstacle
        engine.enqueue("Alice", Command.MOVE_FORWARD);
        engine.tick();
        
        // Alice should still be at (1,2) 
        aliceCopy = engine.getTanksCopy().get("Alice");
        assertEquals(new Position(1, 2), aliceCopy.getPosition());
        
        // Turn Alice right - should become SOUTH
        engine.enqueue("Alice", Command.TURN_RIGHT);
        engine.tick();
        
        // Alice should now be SOUTH
        aliceCopy = engine.getTanksCopy().get("Alice");
        assertEquals(Orientation.SOUTH, aliceCopy.getOrientation());
        
        // Reset the game
        engine.reset();
        
        // After reset, Alice should be back at (1,2) EAST with health 3
        aliceCopy = engine.getTanksCopy().get("Alice");
        assertEquals(new Position(1, 2), aliceCopy.getPosition());
        assertEquals(Orientation.EAST, aliceCopy.getOrientation());
        assertEquals(3, aliceCopy.getHealth());
        
        // Score should be zero
        assertEquals(0, engine.getScoreBoardCopy().getHits("Alice"));
        assertEquals(0, engine.getScoreBoardCopy().getKills("Alice"));
        assertEquals(0, engine.getScoreBoardCopy().getHits("Bob"));
        assertEquals(0, engine.getScoreBoardCopy().getKills("Bob"));
        
        // No projectiles
        assertTrue(engine.getProjectilesCopy().isEmpty());
    }

    @Test
    public void testHitKillFixture() {
        // Empty arena (6,5)
        // Alice at (1,2) EAST health3
        // Bob at (3,2) WEST health1
        
        Arena arena = new Arena(6, 5, ObstacleMap.empty());
        
        Tank alice = new Tank("Alice", new Position(1, 2), Orientation.EAST, 3);
        Tank bob = new Tank("Bob", new Position(3, 2), Orientation.WEST, 1);
        
        GameEngine engine = new GameEngine(arena, Arrays.asList(alice, bob));
        
        // Alice fires
        engine.enqueue("Alice", Command.FIRE);
        engine.tick();
        
        // Bob should now have 0 health
        Tank bobCopy = engine.getTanksCopy().get("Bob");
        assertEquals(0, bobCopy.getHealth());
        
        // Alice should have 1 hit and 1 kill
        assertEquals(1, engine.getScoreBoardCopy().getHits("Alice"));
        assertEquals(1, engine.getScoreBoardCopy().getKills("Alice"));
        assertEquals(6, engine.getScoreBoardCopy().getScore("Alice")); // 1 + 5*1
        
        // No projectiles should remain
        assertTrue(engine.getProjectilesCopy().isEmpty());
        
        // Alice should be the winner
        assertEquals("Alice", engine.winner());
    }
}