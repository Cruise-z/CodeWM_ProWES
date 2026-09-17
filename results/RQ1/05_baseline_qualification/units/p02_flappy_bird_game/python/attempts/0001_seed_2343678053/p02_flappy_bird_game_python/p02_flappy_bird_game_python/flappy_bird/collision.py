"""Collision detection rules for the Flappy Bird game."""

from typing import final

from flappy_bird.pipes import Pipe


def hits_bounds(y: float, ceiling: float, floor: float) -> bool:
    """Check if a bird position hits the world boundaries.
    
    Args:
        y: The bird's vertical position.
        ceiling: The world ceiling position.
        floor: The world floor position.
        
    Returns:
        True if the bird hits the ceiling or floor, False otherwise.
    """
    return y <= ceiling or y >= floor


def hits_pipe(bird_x: float, bird_y: float, pipe: Pipe) -> bool:
    """Check if a bird collides with a pipe.
    
    A collision occurs if the bird overlaps the pipe's solid regions
    horizontally and is not within the vertical gap centered at pipe.gap_y
    of height pipe.gap_height.
    
    Args:
        bird_x: The bird's x-coordinate.
        bird_y: The bird's y-coordinate.
        pipe: The pipe to check collision against.
        
    Returns:
        True if the bird collides with the pipe, False otherwise.
    """
    # Check horizontal overlap
    if not (pipe.x <= bird_x <= pipe.x + pipe.width):
        return False
    
    # Check vertical overlap with gap
    gap_top = pipe.gap_y + pipe.gap_height / 2
    gap_bottom = pipe.gap_y - pipe.gap_height / 2
    
    # Collision occurs if bird is not within the gap vertically
    return not (gap_bottom <= bird_y <= gap_top)