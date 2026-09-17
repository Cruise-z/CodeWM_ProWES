"""Command marker and concrete commands."""

from typing import Optional
from .directions import Direction


class Command:
    """Marker class for all commands.

    This class is instantiable and serves as a base for all concrete command types.
    It has no execute method and is not an abstract base class.
    """

    pass


class MoveForward(Command):
    """Command to move a tank forward."""

    def __init__(self, steps: int = 1):
        """Initialize a MoveForward command.

        Args:
            steps: Number of steps to move forward (default: 1).

        Raises:
            ValueError: If steps is less than 1.
        """
        if steps < 1:
            raise ValueError("Steps must be at least 1")
        self.steps = steps


class RotateLeft(Command):
    """Command to rotate a tank 90 degrees to the left."""

    pass


class RotateRight(Command):
    """Command to rotate a tank 90 degrees to the right."""

    pass


class RotateTo(Command):
    """Command to rotate a tank to a specific direction."""

    def __init__(self, direction: Direction):
        """Initialize a RotateTo command.

        Args:
            direction: The direction to rotate to.
        """
        self.direction = direction


class Fire(Command):
    """Command to fire a projectile from a tank."""

    pass