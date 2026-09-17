"""Board representation and operations for the Caro game."""

from typing import List, Optional
from .types import Player


class Board:
    """Represents the game board for Caro.

    The board is a square grid of a specified size, initialized with empty cells.
    Each cell can contain a Player (X or O) or be empty (None).
    """

    def __init__(self, size: int = 15) -> None:
        """Initialize the board with a given size.

        Args:
            size: The dimension of the square board. Must be at least 1.
        """
        if size < 1:
            raise ValueError("Board size must be at least 1")
        self.size = size
        # Initialize grid with None values representing empty cells
        self.grid: List[List[Optional[Player]]] = [
            [None for _ in range(size)] for _ in range(size)
        ]

    def in_bounds(self, row: int, col: int) -> bool:
        """Check if the given coordinates are within the board boundaries.

        Args:
            row: The row index to check.
            col: The column index to check.

        Returns:
            True if both row and col are within valid bounds, False otherwise.
        """
        return 0 <= row < self.size and 0 <= col < self.size

    def get_cell(self, row: int, col: int) -> Optional[Player]:
        """Get the player occupying a specific cell.

        Precondition: The coordinates must be in bounds.
        This method assumes the caller has verified the coordinates are valid.

        Args:
            row: The row index of the cell.
            col: The column index of the cell.

        Returns:
            The player who occupies the cell, or None if it's empty.
        """
        return self.grid[row][col]

    def is_empty(self, row: int, col: int) -> bool:
        """Check if a specific cell is empty.

        Precondition: The coordinates must be in bounds.
        This method assumes the caller has verified the coordinates are valid.

        Args:
            row: The row index of the cell.
            col: The column index of the cell.

        Returns:
            True if the cell is empty (None), False otherwise.
        """
        return self.grid[row][col] is None

    def set_cell(self, row: int, col: int, player: Player) -> None:
        """Set a player in a specific cell.

        Precondition: The coordinates must be in bounds and the cell must be empty.
        This method assumes the caller has verified these conditions.

        Args:
            row: The row index of the cell.
            col: The column index of the cell.
            player: The player to place in the cell.
        """
        self.grid[row][col] = player

    def is_full(self) -> bool:
        """Check if the board is completely filled with players.

        Returns:
            True if all cells are occupied, False otherwise.
        """
        for row in self.grid:
            if None in row:
                return False
        return True

    def to_matrix(self) -> List[List[Optional[Player]]]:
        """Create a deep copy of the board's grid.

        Returns:
            A new 2D list representing the current state of the board.
        """
        # Create a deep copy of the grid
        return [row[:] for row in self.grid]