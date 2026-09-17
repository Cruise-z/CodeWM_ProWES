"""Scoring rules for the Flappy Bird game."""

from typing import Union


def is_pipe_scored(bird_x: float, pipe_right_edge: float, already_passed: bool) -> bool:
    """Determine if a pipe should be scored based on bird position.

    Implements a strict-left rule: scoring occurs only after the pipe's
    right edge is strictly left of the bird's x position. Once scored,
    a pipe remains marked as passed and will not be scored again.

    Args:
        bird_x: The x-coordinate of the bird.
        pipe_right_edge: The x-coordinate of the pipe's right edge.
        already_passed: Whether the pipe has already been scored.

    Returns:
        True if the pipe should be scored (strictly left and not already passed),
        False otherwise.
    """
    return not already_passed and pipe_right_edge < bird_x