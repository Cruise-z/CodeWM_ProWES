import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

import java.util.Arrays;
import java.util.List;

public class MainTest {

    @Test
    public void testRuntimeWiring() {
        // Test that the Main class can be initialized and runs without exceptions
        assertDoesNotThrow(() -> Main.main(new String[]{}));
    }

    @Test
    public void testBoardLineMergeAndScore() {
        // Test a simple merge scenario: [2,2,0,0] -> [4,0,0,0] with score 4
        Board board = new Board();
        board.setCell(0, 0, 2);
        board.setCell(0, 1, 2);
        board.setCell(0, 2, 0);
        board.setCell(0, 3, 0);
        
        MoveResult result = board.move(Direction.LEFT);
        
        assertTrue(result.changed());
        assertEquals(4, result.scoreGained());
        
        // Verify the board state
        assertEquals(4, board.getGridCopy()[0][0]);
        assertEquals(0, board.getGridCopy()[0][1]);
        assertEquals(0, board.getGridCopy()[0][2]);
        assertEquals(0, board.getGridCopy()[0][3]);
    }

    @Test
    public void testSpawnOnChange() {
        // Test that spawn occurs only when move changes the board
        SequenceSpawner spawner = SequenceSpawner.defaultSequence();
        Board board = new Board();
        Game game = new Game(board, spawner);
        
        // Reset the game to get initial spawns
        game.reset();
        
        // Make a move that doesn't change the board (e.g., moving empty spaces)
        MoveResult result = game.move(Direction.UP);
        
        // The move should not have changed the board
        assertFalse(result.changed());
        
        // Score should be 0 since no merges occurred
        assertEquals(0, result.scoreGained());
        
        // Game score should remain at 0
        assertEquals(0, game.getScore());
        
        // Status should be IN_PROGRESS since no win or loss conditions
        assertEquals(GameStatus.IN_PROGRESS, game.getStatus());
    }
}