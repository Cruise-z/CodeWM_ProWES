"""Pure rules for detecting winning conditions in the Caro game."""

from typing import Tuple
from .board import Board
from .types import Player


def has_five_or_more(board: Board, row: int, col: int, player: Player) -> bool:
    """Check if placing player at (row, col) creates a line of 5 or more stones.

    This function examines all four principal directions from the given position:
    horizontal (0,1), vertical (1,0), diagonal down-right (1,1), and diagonal up-right (-1,1).

    Args:
        board: The game board to check.
        row: The row index where the player is placed.
        col: The column index where the player is placed.
        player: The player who placed the stone.

    Returns:
        True if there are 5 or more consecutive stones of the same player
        in any of the four directions, including the newly placed stone.
    """
    # Define the four principal directions: right, down, down-right, up-right
    directions: Tuple[Tuple[int, int], ...] = ((0, 1), (1, 0), (1, 1), (-1, 1))
    
    for dx, dy in directions:
        count = 1  # Count the newly placed stone
        
        # Check in positive direction
        r, c = row + dx, col + dy
        while board.in_bounds(r, c) and board.get_cell(r, c) == player:
            count += 1
            r += dx
            c += dy
            
        # Check in negative direction
        r, c = row - dx, col - dy
        while board.in_bounds(r, c) and board.get_cell(r, c) == player:
            count += 1
            r -= dx
            c -= dy
            
        if count >= 5:
            return True
            
    return False