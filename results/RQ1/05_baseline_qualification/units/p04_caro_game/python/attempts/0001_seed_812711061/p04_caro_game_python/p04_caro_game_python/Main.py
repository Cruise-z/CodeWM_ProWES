"""Runtime bootstrap executing the canonical nine-move demo and printing once."""

from caro import CaroGame, Player


def run_demo() -> CaroGame:
    """Execute the canonical nine-move sequence and return the final game state.
    
    The sequence results in a horizontal win for Player.X on the ninth move.
    The game is played on a 15x15 board with Player.X starting first.
    
    Returns:
        The CaroGame instance in its final state after the nine moves.
    """
    # Construct game with default 15x15 board and X as first player
    game = CaroGame()
    
    # Canonical nine-move horizontal win sequence for X
    # Positions: (0,0) through (0,8) - all in same row
    moves = [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2), (1, 2), (0, 3), (1, 3), (0, 4)]
    
    for row, col in moves:
        game.move(row, col)
    
    return game


if __name__ == "__main__":
    # Execute the canonical demo and print final status
    final_game = run_demo()
    print(f"Status: {final_game.status().value}")