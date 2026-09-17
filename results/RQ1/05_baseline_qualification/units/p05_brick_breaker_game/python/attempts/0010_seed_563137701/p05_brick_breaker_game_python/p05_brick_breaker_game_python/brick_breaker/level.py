"""Level module for the brick breaker game.

This module defines the Level class and the make_grid_level function
which creates a grid of bricks based on the game configuration.
"""

from .config import GameConfig
from .brick import Brick


class Level:
    """Represents a level containing a collection of bricks."""

    def __init__(self, bricks: list[Brick]):
        """Initialize a level with a list of bricks.

        Args:
            bricks: List of Brick objects in the level.
        """
        self.bricks = bricks

    def remaining(self) -> int:
        """Count the number of alive bricks in the level.

        Returns:
            The number of bricks that are still alive.
        """
        return sum(1 for brick in self.bricks if brick.alive())


def make_grid_level(config: GameConfig) -> Level:
    """Create a grid of bricks based on the game configuration.

    Args:
        config: Game configuration providing brick layout parameters.

    Returns:
        A Level object containing the grid of bricks.
    """
    # Calculate brick width if not specified
    if config.brick_width is None:
        total_width = config.width - 2 * config.brick_padding
        config.brick_width = (
            total_width - (config.brick_cols - 1) * config.brick_padding
        ) / config.brick_cols

    bricks = []
    for row in range(config.brick_rows):
        for col in range(config.brick_cols):
            x = config.brick_padding + col * (config.brick_width + config.brick_padding)
            y = config.top_margin + row * (config.brick_height + config.brick_padding)
            brick = Brick(x, y, config.brick_width, config.brick_height)
            bricks.append(brick)

    return Level(bricks)