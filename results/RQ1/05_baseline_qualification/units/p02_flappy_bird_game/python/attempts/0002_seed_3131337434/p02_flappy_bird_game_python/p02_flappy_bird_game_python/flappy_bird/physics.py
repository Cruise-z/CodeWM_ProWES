"""Vertical physics utilities for the Flappy Bird game."""

from typing import Union


def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a value between a lower and upper bound.

    Args:
        value: The value to clamp.
        lo: The lower bound.
        hi: The upper bound.

    Returns:
        The clamped value.
    """
    return max(lo, min(hi, value))


def integrate_vy(vy: float, gravity: float, max_vy: float) -> float:
    """Integrate vertical velocity with gravity and clamp the result.

    Applies gravity to the current vertical velocity and clamps it
    to ensure it doesn't exceed the maximum allowed vertical velocity.

    Args:
        vy: Current vertical velocity.
        gravity: Gravity constant to apply.
        max_vy: Maximum allowed vertical velocity.

    Returns:
        New vertical velocity after applying gravity and clamping.
    """
    return clamp(vy + gravity, -max_vy, max_vy)