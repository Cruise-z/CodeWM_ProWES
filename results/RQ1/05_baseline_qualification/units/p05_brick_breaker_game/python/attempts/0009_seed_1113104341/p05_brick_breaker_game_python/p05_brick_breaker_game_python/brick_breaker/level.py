"""Level module for the brick breaker game."""

from typing import List
from .config import GameConfig
from .brick import Brick


class Level:
    """Represents a level containing a grid of bricks."""

    def __init__(self, bricks: List[Brick]):
        """Initialize the level with a list of bricks."""
        self.bricks = bricks

    def remaining(self) -> int:
        """
        Count the number of alive bricks in the level.
        
        Returns:
            The number of bricks that are still alive
        """
        return sum(1 for brick in self.bricks if brick.alive())


def make_grid_level(config: GameConfig) -> Level:
    """
    Create a grid of bricks based on the game configuration.
    
    Args:
        config: Game configuration parameters
        
    Returns:
        A Level object containing the grid of bricks
    """
    # Calculate brick width if not provided
    if config.brick_width is None:
        total_width = config.brick_cols * config.brick_width + (config.brick_cols - 1) * config.brick_padding
        brick_width = (config.width - total_width) / config.brick_cols
    else:
        brick_width = config.brick_width
    
    # Create bricks in a grid pattern
    bricks = []
    for row in range(config.brick_rows):
        for col in range(config.brick_cols):
            x = col * (brick_width + config.brick_padding) + config.brick_padding
            y = row * (config.brick_height + config.brick_padding) + config.top_margin
            brick = Brick(x, y, brick_width, config.brick_height)
            bricks.append(brick)
    
    return Level(bricks)