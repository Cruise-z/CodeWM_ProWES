"""Scoring rules for the Flappy Bird game."""

from typing import Union


def is_pipe_scored(bird_x: float, pipe_right_edge: float, already_passed: bool) -> bool:
    """Determine if a pipe should be scored based on bird position.

    Implements a strict-left rule: a pipe is scored exactly once when the
    bird passes its right edge, but only if it hasn't been scored already.

    Args:
        bird_x: The x-coordinate of the bird.
        pipe_right_edge: The x-coordinate of the pipe's right edge.
        already_passed: Whether the pipe has already been scored.

    Returns:
        True if the pipe should be scored (strictly left rule and not already passed),
        False otherwise.

    Example:
        >>> is_pipe_scored(150.0, 100.0, False)
        True
        >>> is_pipe_scored(150.0, 100.0, True)
        False
        >>> is_pipe_scored(100.0, 150.0, False)
        False
    """
    return not already_passed and pipe_right_edge < bird_x