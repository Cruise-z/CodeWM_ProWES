"""Pipe entity for the Flappy Bird game."""

from dataclasses import dataclass
from typing import Final


@dataclass
class Pipe:
    """A pipe obstacle in the Flappy Bird game.

    Pipes have a horizontal position, vertical gap, and width.
    They also track whether the bird has passed through them.
    """

    x: float
    gap_y: float
    width: float
    gap_height: float
    passed: bool = False

    def right_edge(self) -> float:
        """Calculate the x-coordinate of the pipe's right edge.

        Returns:
            The x-coordinate of the pipe's right edge.
        """
        return self.x + self.width

    def step(self, speed: float) -> None:
        """Move the pipe horizontally to the left.

        This method modifies the pipe's x-coordinate in-place.

        Args:
            speed: The speed at which to move the pipe (assumed positive).
        """
        self.x -= speed