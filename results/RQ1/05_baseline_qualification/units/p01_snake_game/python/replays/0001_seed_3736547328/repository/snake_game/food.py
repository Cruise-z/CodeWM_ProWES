"""Food placement utilities for the snake game."""

from typing import Set
from snake_game.grid import Grid, Position
from snake_game.random_provider import RandomProvider


def place_food(grid: Grid, rng: RandomProvider, occupied: Set[Position]) -> Position:
    """Place food at a position that is not occupied by the snake.

    Args:
        grid: The grid where food should be placed.
        rng: The random provider to use for generating positions.
        occupied: A set of positions that are currently occupied by the snake.

    Returns:
        A Position object representing the location of the newly placed food.
    """
    while True:
        candidate = rng.next_position(grid)
        if candidate not in occupied:
            return candidate