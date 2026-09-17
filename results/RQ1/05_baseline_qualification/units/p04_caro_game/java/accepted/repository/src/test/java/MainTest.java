import static org.junit.jupiter.api.Assertions.*;

import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.Test;

/**
 * Automated tests for the Caro game core.
 * Tests cover the runtime entry behavior, nine-move win sequence, and state fixture.
 */
public class MainTest {

    /**
     * Test 1: Main.main returns normally without System.exit.
     * Invoking Main.main with no args produces at most one concise print and no System.exit.
     */
    @Test
    public void testMainReturnsNormally() {
        // Just invoke main and ensure it doesn't throw or exit
        Main.main(new String[0]);
        // If we reach here, main returned normally
    }

    /**
     * Test 2: Exact nine-move horizontal win sequence on new Game(15).
     * Sequence: (7,3),(0,0),(7,4),(0,2),(7,5),(0,4),(7,6),(0,6),(7,7)
     * Assert all placeMove calls return true.
     * Final state should be X_WON with winner Optional.of(Player.X), currentPlayer Player.X, history size 9.
     * Then perform one terminal placeMove attempt and assert it returns false with no mutation.
     */
    @Test
    public void testNineMoveHorizontalWinSequence() {
        Game game = new Game(15);
        
        // Execute the exact nine-move sequence
        assertTrue(game.placeMove(7, 3)); // X
        assertTrue(game.placeMove(0, 0)); // O
        assertTrue(game.placeMove(7, 4)); // X
        assertTrue(game.placeMove(0, 2)); // O
        assertTrue(game.placeMove(7, 5)); // X
        assertTrue(game.placeMove(0, 4)); // O
        assertTrue(game.placeMove(7, 6)); // X
        assertTrue(game.placeMove(0, 6)); // O
        assertTrue(game.placeMove(7, 7)); // X - should win
        
        // Verify final state
        assertEquals(GameState.Status.X_WON, game.getState().getStatus());
        assertEquals(Optional.of(Player.X), game.getState().getWinner());
        assertEquals(Player.X, game.getCurrentPlayer());
        assertEquals(9, game.getHistory().size());
        
        // Terminal move should fail
        assertFalse(game.placeMove(0, 1));
        
        // Verify no mutation occurred
        assertEquals(GameState.Status.X_WON, game.getState().getStatus());
        assertEquals(Optional.of(Player.X), game.getState().getWinner());
        assertEquals(Player.X, game.getCurrentPlayer());
        assertEquals(9, game.getHistory().size());
    }

    /**
     * Test 3: Literal state fixture on new Game(15).
     * Starts with X.
     * placeMove(1,1) true -> turn O.
     * Then placeMove(1,1) and placeMove(-1,0) are false, turn remains O, history size 1.
     * placeMove(2,2) true -> turn X.
     * undo true clears (2,2), restores turn O, history size 1, IN_PROGRESS.
     * reset restores X, empties (1,1), clears history, IN_PROGRESS.
     */
    @Test
    public void testStateFixture() {
        Game game = new Game(15);
        
        // Start with X
        assertEquals(Player.X, game.getCurrentPlayer());
        
        // Place first move
        assertTrue(game.placeMove(1, 1));
        assertEquals(Player.O, game.getCurrentPlayer());
        assertEquals(1, game.getHistory().size());
        
        // Try to place at same position (should fail)
        assertFalse(game.placeMove(1, 1));
        assertEquals(Player.O, game.getCurrentPlayer());
        assertEquals(1, game.getHistory().size());
        
        // Try to place out of bounds (should fail)
        assertFalse(game.placeMove(-1, 0));
        assertEquals(Player.O, game.getCurrentPlayer());
        assertEquals(1, game.getHistory().size());
        
        // Place second move
        assertTrue(game.placeMove(2, 2));
        assertEquals(Player.X, game.getCurrentPlayer());
        assertEquals(2, game.getHistory().size());
        
        // Undo last move
        assertTrue(game.undo());
        assertEquals(Player.O, game.getCurrentPlayer());
        assertEquals(1, game.getHistory().size());
        assertEquals(GameState.Status.IN_PROGRESS, game.getState().getStatus());
        assertNull(game.getBoard().getCell(2, 2));
        
        // Reset game
        game.reset();
        assertEquals(Player.X, game.getCurrentPlayer());
        assertEquals(GameState.Status.IN_PROGRESS, game.getState().getStatus());
        assertEquals(0, game.getHistory().size());
        
        // Verify board is cleared
        assertTrue(game.getBoard().isEmpty(1, 1));
        assertTrue(game.getBoard().isEmpty(2, 2));
    }
}