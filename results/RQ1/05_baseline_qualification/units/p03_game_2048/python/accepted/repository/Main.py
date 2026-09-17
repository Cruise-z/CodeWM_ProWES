"""Entry point for running a 2048 game demo."""

from typing import Tuple
from twenty48.game import Game
from twenty48.types import Direction, GameStatus


def run_demo(seed: int) -> Tuple[GameStatus, int, int]:
    """
    Run a single left move demo of the 2048 game with a given seed.

    Args:
        seed: The seed for the random number generator to ensure deterministic behavior.

    Returns:
        A tuple of (status, score, tiles_count) where:
        - status: The final game status after the move
        - score: The current score after the move
        - tiles_count: The number of non-zero tiles on the board after the move
    """
    # Create a new game with the specified seed
    game = Game(seed)
    
    # Reset the game to initial state
    game.reset()
    
    # Perform exactly one move to the left
    game.move(Direction.LEFT)
    
    # Get the current status, score, and count of non-zero tiles
    status = game.get_status()
    score = game.get_score()
    
    # Count the number of non-zero tiles on the board
    board = game.get_board()
    tiles_count = 0
    for row in board.get_grid():
        for cell in row:
            if cell != 0:
                tiles_count += 1
    
    # Return the results as a tuple
    return (status, score, tiles_count)