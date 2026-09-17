"""Collision detection rules for the Flappy Bird game."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flappy_bird.pipes import Pipe

def hits_bounds(y: float, ceiling: float, floor: float) -> bool:
    """Check if a vertical position hits the world bounds.

    Args:
        y: The vertical position to check.
        ceiling: The upper boundary of the world.
        floor: The lower boundary of the world.

    Returns:
        True if the position is outside the valid vertical range.
    """
    return y < ceiling or y > floor


def hits_pipe(bird_x: float, bird_y: float, pipe: "Pipe") -> bool:
    """Check if the bird collides with a pipe.

    A collision occurs if the bird's position overlaps with the pipe's solid
    regions. The bird is not considered to have hit a pipe if it is within
    the vertical gap of the pipe.

    Args:
        bird_x: The x-coordinate of the bird.
        bird_y: The y-coordinate of the bird.
        pipe: The pipe to check collision against.

    Returns:
        True if the bird collides with the pipe.
    """
    # Check if bird is horizontally aligned with the pipe
    if not (pipe.x <= bird_x <= pipe.x + pipe.width):
        return False

    # Check if bird is vertically within the pipe's gap
    # The gap is centered at pipe.gap_y with height pipe.gap_height
    gap_top = pipe.gap_y + pipe.gap_height / 2
    gap_bottom = pipe.gap_y - pipe.gap_height / 2
    
    # Bird is inside the gap, so no collision
    if gap_bottom <= bird_y <= gap_top:
        return False
    
    # Bird is above or below the pipe, so collision
    return True