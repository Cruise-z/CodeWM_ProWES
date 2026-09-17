"""Scoring rules for the Flappy Bird game."""

from typing import bool


def is_pipe_scored(bird_x: float, pipe_right_edge: float, already_passed: bool) -> bool:
    """Determine if a pipe should be scored based on the bird's position.

    Implements a strict-left rule: a pipe is scored exactly once when the bird
    passes the right edge of the pipe, and only if it hasn't been scored already.

    Args:
        bird_x: The x-coordinate of the bird.
        pipe_right_edge: The x-coordinate of the pipe's right edge.
        already_passed: Whether the pipe has already been scored.

    Returns:
        True if the pipe should be scored, False otherwise.
    """
    return not already_passed and pipe_right_edge < bird_x