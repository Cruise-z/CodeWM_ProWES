"""Pipe entity for the Flappy Bird game."""

from typing import Optional
from dataclasses import dataclass


@dataclass
class Pipe:
    """A pipe obstacle in the Flappy Bird game.

    Pipes have a horizontal position, vertical gap position, width,
    gap height, and a flag indicating if the bird has passed through them.
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

        This method modifies the pipe's x coordinate by subtracting the speed.

        Args:
            speed: The speed at which the pipe moves leftward.
        """
        self.x -= speed