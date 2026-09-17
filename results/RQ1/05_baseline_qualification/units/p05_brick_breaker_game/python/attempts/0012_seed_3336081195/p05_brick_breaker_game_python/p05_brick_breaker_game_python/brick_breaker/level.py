"""Level module for the brick breaker game.

This module defines the Level class which represents the game level,
including the collection of bricks and methods to manage them.
"""

from typing import List
from .config import GameConfig
from .brick import Brick


class Level:
    """Represents a level in the brick breaker game.

    A level consists of a collection of bricks that can be checked for
    remaining bricks and managed through the game.
    """

    def __init__(self, bricks: List[Brick]):
        """Initialize a level with a list of bricks.

        Args:
            bricks: List of Brick objects that make up the level.
        """
        self.bricks = bricks

    def remaining(self) -> int:
        """Count the number of bricks that are still alive.

        Returns:
            The number of bricks that have durability > 0.
        """
        return sum(1 for brick in self.bricks if brick.alive())


def make_grid_level(config: GameConfig) -> Level:
    """Create a grid of bricks based on the game configuration.

    This function generates a rectangular grid of bricks positioned at the
    top of the game area according to the configuration parameters.

    Args:
        config: GameConfig object containing level layout parameters.

    Returns:
        A Level object containing the generated bricks.
    """
    # Calculate brick width if not explicitly provided
    if config.brick_width is None:
        total_width = config.width - 2 * config.brick_padding
        available_width = total_width - (config.brick_cols - 1) * config.brick_padding
        brick_width = available_width / config.brick_cols
    else:
        brick_width = config.brick_width

    bricks = []
    for row in range(config.brick_rows):
        for col in range(config.brick_cols):
            # Calculate the x and y position for this brick
            x = config.brick_padding + col * (brick_width + config.brick_padding)
            y = config.top_margin + row * (config.brick_height + config.brick_padding)
            
            # Create the brick with default durability of 1
            brick = Brick(
                x=x,
                y=y,
                width=brick_width,
                height=config.brick_height,
                durability=1
            )
            bricks.append(brick)

    return Level(bricks)