"""Collision detection rules for the Flappy Bird game."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flappy_bird.pipes import Pipe


def hits_bounds(y: float, ceiling: float, floor: float) -> bool:
    """Check if a vertical position hits the world bounds.

    Args:
        y: The vertical position to check.
        ceiling: The ceiling boundary.
        floor: The floor boundary.

    Returns:
        True if the position is outside the valid vertical range.
    """
    return y < ceiling or y > floor


def hits_pipe(bird_x: float, bird_y: float, pipe: "Pipe") -> bool:
    """Check if the bird collides with a pipe.

    A collision occurs if the bird overlaps the pipe's solid regions
    horizontally and is not within the vertical gap centered at pipe.gap_y.

    Args:
        bird_x: The x-coordinate of the bird.
        bird_y: The y-coordinate of the bird.
        pipe: The pipe to check collision against.

    Returns:
        True if there is a collision, False otherwise.
    """
    # Check horizontal overlap
    if not (pipe.x <= bird_x <= pipe.x + pipe.width):
        return False

    # Check vertical overlap with the gap
    gap_top = pipe.gap_y
    gap_bottom = pipe.gap_y + pipe.gap_height

    # Collision occurs if bird is not within the gap
    return not (gap_top <= bird_y <= gap_bottom)