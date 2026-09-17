"""Collision detection utilities for the snake game."""

from typing import List

from snake_game.grid import Grid, Position


def hit_wall(grid: Grid, pos: Position) -> bool:
    """Check if a position is outside the grid boundaries.

    Args:
        grid: The grid to check against.
        pos: The position to check.

    Returns:
        True if the position is outside the grid, False otherwise.
    """
    return not grid.in_bounds(pos)


def hit_self(body: List[Position], next_head: Position, grow: bool) -> bool:
    """Check if the snake would collide with itself in the next move.

    Args:
        body: The current body of the snake.
        next_head: The position the head would move to.
        grow: Whether the snake will grow (True) or not (False).

    Returns:
        True if the snake would collide with itself, False otherwise.
    """
    # If the snake isn't growing, the tail will move one position
    # so we need to exclude the tail from collision checking
    if not grow and len(body) > 1:
        # The tail position that will be removed
        tail = body[-1]
        # Check if the next head position collides with any body segment
        # except the tail which will move away
        for i, segment in enumerate(body):
            if segment == next_head and segment != tail:
                return True
        return False
    else:
        # If growing or no body segments, just check if next head 
        # collides with any body segment
        for segment in body:
            if segment == next_head:
                return True
        return False