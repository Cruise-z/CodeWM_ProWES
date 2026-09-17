"""Level module for the brick breaker game.

This module defines the Level class which aggregates bricks and provides
a factory function to create a grid-based level layout.
"""

from typing import List
from .config import GameConfig
from .brick import Brick


class Level:
    """Represents a level containing a collection of bricks."""

    def __init__(self, bricks: List[Brick]):
        """Initialize a level with a list of bricks.

        Args:
            bricks: List of Brick objects that make up the level.
        """
        self.bricks = bricks

    def remaining(self) -> int:
        """Count the number of alive bricks in the level.

        Returns:
            The number of bricks that have durability > 0.
        """
        return sum(1 for brick in self.bricks if brick.alive())


def make_grid_level(config: GameConfig) -> Level:
    """Create a grid of bricks based on configuration parameters.

    Args:
        config: GameConfig object containing level layout parameters.

    Returns:
        A Level object containing a grid of bricks arranged according to
        the configuration.
    """
    # Calculate brick width if not explicitly provided
    if config.brick_width is None:
        total_width = config.width - 2 * config.brick_padding
        brick_width = (total_width - (config.brick_cols - 1) * config.brick_padding) / config.brick_cols
    else:
        brick_width = config.brick_width

    # Create bricks in a grid pattern
    bricks = []
    for row in range(config.brick_rows):
        for col in range(config.brick_cols):
            x = config.brick_padding + col * (brick_width + config.brick_padding)
            y = config.top_margin + row * (config.brick_height + config.brick_padding)
            brick = Brick(x, y, brick_width, config.brick_height)
            bricks.append(brick)

    return Level(bricks)