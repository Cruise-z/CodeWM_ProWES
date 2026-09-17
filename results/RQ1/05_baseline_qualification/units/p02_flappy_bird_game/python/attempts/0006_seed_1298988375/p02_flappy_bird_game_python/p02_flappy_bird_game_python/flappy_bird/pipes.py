"""Pipe entity for the Flappy Bird game."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Pipe:
    """A pipe obstacle in the Flappy Bird game.

    Pipes have a position (x, gap_y), dimensions (width, gap_height),
    and a flag indicating whether the bird has passed through them.
    """

    x: float
    gap_y: float
    width: float
    gap_height: float
    passed: bool = False

    def right_edge(self) -> float:
        """Calculate the x-coordinate of the pipe's right edge.

        Returns:
            The x-coordinate of the right edge of the pipe.
        """
        return self.x + self.width

    def step(self, speed: float) -> None:
        """Move the pipe horizontally to the left.

        This method modifies the pipe's x-coordinate by subtracting the speed.

        Args:
            speed: The speed at which the pipe moves leftward.
        """
        self.x -= speed