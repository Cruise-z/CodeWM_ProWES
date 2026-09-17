"""Scoring rules for the Flappy Bird game."""

from typing import final


def is_pipe_scored(bird_x: float, pipe_right_edge: float, already_passed: bool) -> bool:
    """Determine if a pipe should be scored based on the bird's position.
    
    Implements a strict-left rule: a pipe is scored exactly once when the 
    bird's x-coordinate passes strictly to the left of the pipe's right edge.
    
    Args:
        bird_x: The x-coordinate of the bird.
        pipe_right_edge: The x-coordinate of the pipe's right edge.
        already_passed: Whether the pipe has already been scored.
        
    Returns:
        True if the pipe should be scored, False otherwise.
        
    Examples:
        >>> is_pipe_scored(150.0, 120.0, False)
        True
        >>> is_pipe_scored(150.0, 120.0, True)
        False
        >>> is_pipe_scored(100.0, 120.0, False)
        False
    """
    return not already_passed and pipe_right_edge < bird_x