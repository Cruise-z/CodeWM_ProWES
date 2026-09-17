"""Board entity for the 2048 game, handling grid operations and moves."""

from typing import List, Tuple
from .types import Direction
from .move import move_line_left


class Board:
    """A 4x4 grid representing the 2048 game board."""

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
        Move tiles in the specified direction.
        
        Args:
            direction: The direction to move tiles
            
        Returns:
            A tuple of (changed, gained_score) where:
            - changed is True if any tile moved or merged
            - gained_score is the total score from merging tiles
        """
        # Save original grid to check if anything changed
        original_grid = self.get_grid()
        
        gained_score = 0
        changed = False
        
        if direction == Direction.LEFT:
            # Process each row
            for i in range(4):
                new_row, score = move_line_left(self._grid[i])
                if new_row != self._grid[i]:
                    changed = True
                self._grid[i] = new_row
                gained_score += score
                
        elif direction == Direction.RIGHT:
            # Process each row in reverse order
            for i in range(4):
                # Reverse the row, apply left move, then reverse back
                reversed_row = self._grid[i][::-1]
                new_row, score = move_line_left(reversed_row)
                # Reverse the result back
                self._grid[i] = new_row[::-1]
                if new_row != reversed_row:
                    changed = True
                gained_score += score
                
        elif direction == Direction.UP:
            # Process each column
            for j in range(4):
                # Extract column
                column = [self._grid[i][j] for i in range(4)]
                new_column, score = move_line_left(column)
                if new_column != column:
                    changed = True
                # Put column back
                for i in range(4):
                    self._grid[i][j] = new_column[i]
                gained_score += score
                
        elif direction == Direction.DOWN:
            # Process each column in reverse order
            for j in range(4):
                # Extract column and reverse it
                column = [self._grid[i][j] for i in range(4)]
                reversed_column = column[::-1]
                new_column, score = move_line_left(reversed_column)
                # Reverse result back and put it back
                final_column = new_column[::-1]
                if final_column != column:
                    changed = True
                for i in range(4):
                    self._grid[i][j] = final_column[i]
                gained_score += score
                
        return (changed, gained_score)

    def can_move(self) -> bool:
        """
        Check if any move is possible.
        
        Returns:
            True if there is at least one empty cell or adjacent tiles that can be merged
        """
        # Check for empty cells
        for i in range(4):
            for j in range(4):
                if self._grid[i][j] == 0:
                    return True
                    
        # Check for horizontal merges
        for i in range(4):
            for j in range(3):
                if self._grid[i][j] == self._grid[i][j+1]:
                    return True
                    
        # Check for vertical merges
        for i in range(3):
            for j in range(4):
                if self._grid[i][j] == self._grid[i+1][j]:
                    return True
                    
        return False

    def has_target(self, target: int = 2048) -> bool:
        """
        Check if any cell contains the target value.
        
        Args:
            target: The target value to look for (default is 2048)
            
        Returns:
            True if any cell contains the target value
        """
        for i in range(4):
            for j in range(4):
                if self._grid[i][j] == target:
                    return True
        return False

    def empty_positions(self) -> List[Tuple[int, int]]:
        """
        Get list of empty positions on the board.
        
        Returns:
            List of (row, col) tuples representing empty cells
        """
        positions = []
        for i in range(4):
            for j in range(4):
                if self._grid[i][j] == 0:
                    positions.append((i, j))
        return positions

    def add_random_tile(self, rng) -> bool:
        """
        Add a random tile (2 or 4) to a random empty position.
        
        Args:
            rng: Random number generator
            
        Returns:
            True if a tile was added, False if board is full
        """
        empty_positions = self.empty_positions()
        if not empty_positions:
            return False
            
        # Choose random empty position
        row, col = rng.choice(empty_positions)
        
        # 90% chance for 2, 10% chance for 4
        tile_value = 2 if rng.random() < 0.9 else 4
        self._grid[row][col] = tile_value
        return True