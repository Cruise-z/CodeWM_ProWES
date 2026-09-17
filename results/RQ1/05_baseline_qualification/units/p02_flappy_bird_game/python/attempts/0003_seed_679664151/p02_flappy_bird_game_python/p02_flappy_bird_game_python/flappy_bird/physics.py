"""Physics utilities for the Flappy Bird game."""

from typing import cast


def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a value to the range [lo, hi].

    Args:
        value: The value to clamp.
        lo: The lower bound.
        hi: The upper bound.

    Returns:
        The clamped value.
    """
    return max(lo, min(hi, value))


def integrate_vy(vy: float, gravity: float, max_vy: float) -> float:
    """Integrate vertical velocity with gravity and clamp.

    Applies gravity to the current vertical velocity and clamps the result
    to the allowed range [-max_vy, max_vy].

    Args:
        vy: Current vertical velocity.
        gravity: Gravity constant.
        max_vy: Maximum allowed vertical velocity.

    Returns:
        New vertical velocity after applying gravity and clamping.
    """
    return clamp(vy + gravity, -max_vy, max_vy)