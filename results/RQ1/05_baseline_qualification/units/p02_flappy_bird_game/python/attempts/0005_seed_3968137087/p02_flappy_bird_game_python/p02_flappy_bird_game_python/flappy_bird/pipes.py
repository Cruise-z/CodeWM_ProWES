"""Pipe entity for the Flappy Bird game."""

from typing import Union


class Pipe:
    """A pipe object in the Flappy Bird game.

    Pipes have a horizontal position, vertical gap location, width, and gap height.
    They also track whether the bird has passed them for scoring purposes.
    """

    def __init__(
        self,
        x: float,
        gap_y: float,
        width: float,
        gap_height: float,
        passed: bool = False,
    ) -> None:
        """Initialize a Pipe with position, size, and passed status.

        Args:
            x: The x-coordinate of the pipe's left edge.
            gap_y: The y-coordinate of the pipe's top gap edge.
            width: The width of the pipe.
            gap_height: The height of the vertical gap in the pipe.
            passed: Whether the bird has already passed this pipe.
        """
        self.x = x
        self.gap_y = gap_y
        self.width = width
        self.gap_height = gap_height
        self.passed = passed

    def right_edge(self) -> float:
        """Calculate the x-coordinate of the pipe's right edge.

        Returns:
            The x-coordinate of the pipe's right edge.
        """
        return self.x + self.width

    def step(self, speed: float) -> None:
        """Move the pipe horizontally to the left by the given speed.

        This method modifies the pipe's x attribute in place.

        Args:
            speed: The speed to move the pipe to the left (positive value).
        """
        self.x -= speed