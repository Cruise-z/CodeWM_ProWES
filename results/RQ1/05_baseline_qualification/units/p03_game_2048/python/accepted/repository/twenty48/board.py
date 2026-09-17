"""Board entity for the 2048 game."""

from typing import List, Tuple, TYPE_CHECKING
from .types import Direction
from .move import move_line_left

if TYPE_CHECKING:
    from random import Random


class Board:
    """Represents the 4x4 grid of the 2048 game."""

    def __init__(self) -> None:
        """Initialize an empty 4x4 board."""
        self._grid: List[List[int]] = [[0 for _ in range(4)] for _ in range(4)]

    def get_grid(self) -> List[List[int]]:
        """Return a deep copy of the board's grid."""
        return [row[:] for row in self._grid]

    def reset_empty(self) -> None:
        """Reset the board to all zeros."""
        for i in range(4):
            for j in range(4):
                self._grid[i][j] = 0

    def move(self, direction: Direction) -> Tuple[bool, int]:
        """
        Apply a move in the given direction.

        Args:
            direction: The direction to move tiles.

        Returns:
            A tuple of (changed, gained_score) where:
            - changed: True if any tile moved or merged
            - gained_score: The total score from all merges in this move
        """
        # Store original grid to detect changes
        original_grid = self.get_grid()

        gained_score = 0
        changed = False

        if direction == Direction.LEFT:
            for i in range(4):
                new_row, score = move_line_left(self._grid[i])
                self._grid[i] = new_row
                gained_score += score
                if new_row != original_grid[i]:
                    changed = True

        elif direction == Direction.RIGHT:
            # Reverse each row, move left, then reverse back
            for i in range(4):
                reversed_row = self._grid[i][::-1]
                new_row, score = move_line_left(reversed_row)
                self._grid[i] = new_row[::-1]
                gained_score += score
                if new_row[::-1] != original_grid[i]:
                    changed = True

        elif direction == Direction.UP:
            # Transpose, move left, transpose back
            transposed = [[self._grid[j][i] for j in range(4)] for i in range(4)]
            for i in range(4):
                new_col, score = move_line_left(transposed[i])
                gained_score += score
                for j in range(4):
                    self._grid[j][i] = new_col[j]
            # Check if any column changed
            new_grid = [[self._grid[j][i] for j in range(4)] for i in range(4)]
            if new_grid != original_grid:
                changed = True

        elif direction == Direction.DOWN:
            # Transpose, reverse each column, move left, reverse back, transpose back
            transposed = [[self._grid[j][i] for j in range(4)] for i in range(4)]
            for i in range(4):
                reversed_col = transposed[i][::-1]
                new_col, score = move_line_left(reversed_col)
                gained_score += score
                for j in range(4):
                    self._grid[j][i] = new_col[::-1][j]
            # Check if any column changed
            new_grid = [[self._grid[j][i] for j in range(4)] for i in range(4)]
            if new_grid != original_grid:
                changed = True

        return changed, gained_score

    def can_move(self) -> bool:
        """
        Check if any move is possible.

        Returns:
            True if there is at least one empty cell or two adjacent equal tiles.
        """
        # Check for empty cells
        for i in range(4):
            for j in range(4):
                if self._grid[i][j] == 0:
                    return True

        # Check for horizontal merges
        for i in range(4):
            for j in range(3):
                if self._grid[i][j] == self._grid[i][j + 1]:
                    return True

        # Check for vertical merges
        for i in range(3):
            for j in range(4):
                if self._grid[i][j] == self._grid[i + 1][j]:
                    return True

        return False

    def has_target(self, target: int = 2048) -> bool:
        """
        Check if any cell contains the target value.

        Args:
            target: The value to search for (default 2048).

        Returns:
            True if any cell contains the target value.
        """
        for i in range(4):
            for j in range(4):
                if self._grid[i][j] == target:
                    return True
        return False

    def empty_positions(self) -> List[Tuple[int, int]]:
        """
        Get all empty positions on the board.

        Returns:
            A list of (row, col) tuples where the cell is empty (value is 0).
        """
        positions = []
        for i in range(4):
            for j in range(4):
                if self._grid[i][j] == 0:
                    positions.append((i, j))
        return positions

    def add_random_tile(self, rng: 'Random') -> bool:
        """
        Add a random tile (2 with 90% probability, 4 with 10%) to a random empty position.

        Args:
            rng: Random number generator.

        Returns:
            True if a tile was successfully added, False if no empty positions exist.
        """
        empty_positions = self.empty_positions()
        if not empty_positions:
            return False

        # Choose a random empty position
        row, col = rng.choice(empty_positions)

        # Generate a random tile (2 with 90% probability, 4 with 10%)
        tile_value = 2 if rng.random() < 0.9 else 4

        # Place the tile
        self._grid[row][col] = tile_value
        return True