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
        True if y is outside the valid vertical range [ceiling, floor].
    """
    return y < ceiling or y > floor


def hits_pipe(bird_x: float, bird_y: float, pipe: "Pipe") -> bool:
    """Check if the bird collides with a pipe.

    A collision occurs if the bird's position overlaps with the pipe's solid
    regions (top and bottom). The bird does not collide if it is within the
    vertical gap of the pipe.

    Args:
        bird_x: The x-coordinate of the bird.
        bird_y: The y-coordinate of the bird.
        pipe: The pipe to check collision against.

    Returns:
        True if the bird collides with the pipe, False otherwise.
    """
    # Check horizontal overlap
    if not (pipe.x <= bird_x <= pipe.x + pipe.width):
        return False

    # Check vertical overlap with top or bottom pipe segments
    # Top pipe segment
    if bird_y <= pipe.gap_y:
        return True
    # Bottom pipe segment
    if bird_y >= pipe.gap_y + pipe.gap_height:
        return True

    # Bird is within the pipe's gap - no collision
    return False