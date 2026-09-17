"""Command marker and concrete commands."""

from typing import Optional
from .directions import Direction


class Command:
    """Marker class for all commands."""

    def __init__(self) -> None:
        """Initialize a command."""
        pass


class MoveForward(Command):
    """Move forward command."""

    def __init__(self, steps: int = 1) -> None:
        """
        Initialize a move forward command.

        Args:
            steps: Number of steps to move forward (default 1).

        Raises:
            ValueError: If steps is less than 1.
        """
        if steps < 1:
            raise ValueError("Steps must be at least 1")
        self.steps = steps


class RotateLeft(Command):
    """Rotate left command."""

    def __init__(self) -> None:
        """Initialize a rotate left command."""
        pass


class RotateRight(Command):
    """Rotate right command."""

    def __init__(self) -> None:
        """Initialize a rotate right command."""
        pass


class RotateTo(Command):
    """Rotate to specific direction command."""

    def __init__(self, direction: Direction) -> None:
        """
        Initialize a rotate to command.

        Args:
            direction: The direction to rotate to.
        """
        self.direction = direction


class Fire(Command):
    """Fire command."""

    def __init__(self) -> None:
        """Initialize a fire command."""
        pass