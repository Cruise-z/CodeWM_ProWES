"""Entry point for running a 2048 game demo with a single left move."""

from typing import Tuple
from twenty48.game import Game
from twenty48.types import Direction, GameStatus


def run_demo(seed: int) -> Tuple[GameStatus, int, int]:
    """
    Run a single left move demo of the 2048 game.
    
    Args:
        seed: Seed for deterministic random number generation
        
    Returns:
        A tuple of (status, score, tiles_count) where:
        - status: The final game status
        - score: The final score after the move
        - tiles_count: The number of non-empty tiles on the board
    """
    # Create game with deterministic seed
    game = Game(seed)
    
    # Reset game to initial state
    game.reset()
    
    # Perform exactly one move to the left
    game.move(Direction.LEFT)
    
    # Calculate tiles count (number of non-zero tiles)
    board_grid = game.get_board().get_grid()
    tiles_count = sum(1 for row in board_grid for cell in row if cell != 0)
    
    # Return status, score, and tiles count
    return (
        game.get_status(),
        game.get_score(),
        tiles_count
    )