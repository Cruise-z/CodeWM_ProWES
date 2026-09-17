"""Automated tests for the Caro game implementation.

This module verifies the core functionality of the Caro game,
including runtime wiring, validation precedence, canonical wins,
and reset behavior.
"""

import pytest
from caro import CaroGame, Player, Status, Move
from caro.errors import InvalidMoveError, GameOverError
from Main import run_demo


def test_runtime_wiring():
    """Test that the runtime demo executes correctly and produces expected outcome."""
    # Run the canonical demo
    final_game = run_demo()
    
    # Verify final status is X_WON
    assert final_game.status() == Status.X_WON
    
    # Verify the game has a winner
    assert final_game.winner() == Player.X
    
    # Verify history contains exactly 9 moves
    assert len(final_game.history()) == 9
    
    # Verify the last move was at (0, 4) by Player.X
    last_move = final_game.history()[-1]
    assert last_move.row == 0
    assert last_move.col == 4
    assert last_move.player == Player.X


def test_validation_precedence():
    """Test that GameOverError is raised before other validations when game is over."""
    game = CaroGame()
    
    # Make moves to create a win for X
    moves = [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2), (1, 2), (0, 3), (1, 3), (0, 4)]
    for row, col in moves:
        game.move(row, col)
    
    # Game should now be in X_WON status
    assert game.status() == Status.X_WON
    
    # Attempting to make another move should raise GameOverError
    with pytest.raises(GameOverError):
        game.move(0, 5)


def test_invalid_move_errors():
    """Test that InvalidMoveError is raised for out-of-bounds and occupied positions."""
    game = CaroGame()
    
    # Test out-of-bounds move
    with pytest.raises(InvalidMoveError):
        game.move(-1, 0)
    
    with pytest.raises(InvalidMoveError):
        game.move(15, 0)
    
    with pytest.raises(InvalidMoveError):
        game.move(0, 15)
    
    # Test occupied position
    game.move(0, 0)  # First move should succeed
    with pytest.raises(InvalidMoveError):
        game.move(0, 0)  # Trying to occupy same position should fail


def test_canonical_nine_move_horizontal_win():
    """Test the canonical nine-move horizontal win sequence."""
    game = CaroGame()
    
    # Test moves 1 through 8 (no win yet)
    moves = [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2), (1, 2), (0, 3), (1, 3)]
    for i, (row, col) in enumerate(moves):
        game.move(row, col)
        # After each move, game should still be in progress
        assert game.status() == Status.IN_PROGRESS
        assert game.winner() is None
    
    # On the ninth move, X should win horizontally
    game.move(0, 4)
    assert game.status() == Status.X_WON
    assert game.winner() == Player.X


def test_reset_behavior():
    """Test that reset restores the game to initial clean state."""
    game = CaroGame()
    
    # Make several moves
    moves = [(0, 0), (1, 0), (0, 1)]
    for row, col in moves:
        game.move(row, col)
    
    # Verify game is in progress and has history
    assert game.status() == Status.IN_PROGRESS
    assert len(game.history()) == 3
    
    # Reset the game
    game.reset()
    
    # Verify reset state
    assert game.status() == Status.IN_PROGRESS
    assert game.winner() is None
    assert len(game.history()) == 0
    assert game.current_player() == Player.X
    
    # Verify board is empty
    board_state = game.board()
    for row in board_state:
        for cell in row:
            assert cell is None