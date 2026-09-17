"""Level management for the Brick Breaker game."""

from typing import List
from .config import GameConfig
from .brick import Brick


class Level:
    """Represents a level in the Brick Breaker game.

    A level consists of a collection of bricks that can be checked for
    remaining bricks and managed during gameplay.
    """

    def __init__(self, bricks: List[Brick]):
        """Initialize the level with a list of bricks.

        Args:
            bricks: A list of Brick objects that make up the level.
        """
        self.bricks = bricks

    def remaining(self) -> int:
        """Count the number of alive bricks in the level.

        Returns:
            The number of bricks that are still alive (have durability > 0).
        """
        return sum(1 for brick in self.bricks if brick.alive())


def make_grid_level(config: GameConfig) -> Level:
    """Create a grid of bricks based on the game configuration.

    Args:
        config: The game configuration containing brick layout parameters.

    Returns:
        A Level object containing the arranged bricks.
    """
    # Calculate brick dimensions if not provided
    brick_width = config.brick_width
    brick_height = config.brick_height
    brick_padding = config.brick_padding
    top_margin = config.top_margin
    
    # Create bricks in a grid pattern
    bricks = []
    
    # Calculate starting x position to center the grid
    total_width = config.brick_cols * brick_width + (config.brick_cols - 1) * brick_padding
    start_x = (config.width - total_width) / 2
    
    for row in range(config.brick_rows):
        for col in range(config.brick_cols):
            x = start_x + col * (brick_width + brick_padding)
            y = top_margin + row * (brick_height + brick_padding)
            brick = Brick(x, y, brick_width, brick_height)
            bricks.append(brick)
    
    return Level(bricks)