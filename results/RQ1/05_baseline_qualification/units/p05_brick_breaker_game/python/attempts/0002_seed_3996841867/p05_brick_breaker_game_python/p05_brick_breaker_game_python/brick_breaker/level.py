"""Level implementation for the brick breaker game.

This module defines the Level class which manages a collection of bricks
and provides functionality to create a grid layout of bricks.
"""

from .config import GameConfig
from .brick import Brick


class Level:
    """Represents a level in the brick breaker game, containing bricks."""

    def __init__(self, bricks: list[Brick]):
        """Initialize a level with a list of bricks.

        Args:
            bricks: List of Brick objects making up the level.
        """
        self.bricks = bricks

    def remaining(self) -> int:
        """Count the number of bricks that are still alive.

        Returns:
            The number of bricks with durability > 0.
        """
        return sum(1 for brick in self.bricks if brick.alive())


def make_grid_level(config: GameConfig) -> Level:
    """Create a grid of bricks based on configuration parameters.

    Args:
        config: GameConfig object containing level layout parameters.

    Returns:
        A Level object populated with bricks arranged in a grid pattern.
    """
    # Calculate brick width if not explicitly provided
    if config.brick_width is None:
        total_width = config.brick_cols * config.brick_width + (config.brick_cols - 1) * config.brick_padding
        brick_width = (config.width - total_width) / config.brick_cols
    else:
        brick_width = config.brick_width

    # Create bricks in a grid pattern
    bricks = []
    for row in range(config.brick_rows):
        for col in range(config.brick_cols):
            # Calculate x and y position for this brick
            x = col * (brick_width + config.brick_padding) + config.brick_padding
            y = row * (config.brick_height + config.brick_padding) + config.top_margin
            
            # Create brick and add to list
            brick = Brick(x, y, brick_width, config.brick_height)
            bricks.append(brick)

    return Level(bricks)