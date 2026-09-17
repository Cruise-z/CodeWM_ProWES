"""Collision detection rules for the Flappy Bird game."""

from typing import Union
from flappy_bird.pipes import Pipe


def hits_bounds(y: float, ceiling: float, floor: float) -> bool:
    """Check if a vertical position hits the world bounds.

    Args:
        y: The vertical position to check.
        ceiling: The ceiling of the world.
        floor: The floor of the world.

    Returns:
        True if the position is outside the world bounds, False otherwise.
    """
    return y < ceiling or y > floor


def hits_pipe(bird_x: float, bird_y: float, pipe: Pipe) -> bool:
    """Check if the bird collides with a pipe.

    A collision occurs if the bird's position overlaps with the pipe's solid
    regions (top and bottom parts), excluding the gap area.

    Args:
        bird_x: The x-coordinate of the bird.
        bird_y: The y-coordinate of the bird.
        pipe: The pipe to check collision against.

    Returns:
        True if the bird collides with the pipe, False otherwise.
    """
    # Check if bird is horizontally aligned with the pipe
    if not (pipe.x <= bird_x <= pipe.x + pipe.width):
        return False
    
    # Check if bird is vertically in the solid regions of the pipe
    # Top part of the pipe (above gap)
    if bird_y <= pipe.gap_y:
        return True
    
    # Bottom part of the pipe (below gap)
    if bird_y >= pipe.gap_y + pipe.gap_height:
        return True
    
    # Bird is within the gap, no collision
    return False