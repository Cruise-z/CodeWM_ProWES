"""Pipe entity for the Flappy Bird game."""

from typing import Final


class Pipe:
    """A pipe obstacle in the Flappy Bird game.

    Pipes have a horizontal position, vertical gap, and width. They also track
    whether the bird has passed them for scoring purposes.
    """

    def __init__(
        self,
        x: float,
        gap_y: float,
        width: float,
        gap_height: float,
        passed: bool = False,
    ) -> None:
        """Initialize a Pipe.

        Args:
            x: The left x-coordinate of the pipe.
            gap_y: The top y-coordinate of the gap.
            width: The width of the pipe.
            gap_height: The height of the gap.
            passed: Whether the bird has already passed this pipe.
        """
        self.x: Final[float] = x
        self.gap_y: Final[float] = gap_y
        self.width: Final[float] = width
        self.gap_height: Final[float] = gap_height
        self.passed: Final[bool] = passed

    def right_edge(self) -> float:
        """Calculate the right edge x-coordinate of the pipe.

        Returns:
            The x-coordinate of the right edge of the pipe.
        """
        return self.x + self.width

    def step(self, speed: float) -> None:
        """Move the pipe horizontally to the left.

        This method mutates the pipe's x position.

        Args:
            speed: The speed to move the pipe to the left (positive value).
        """
        self.x -= speed