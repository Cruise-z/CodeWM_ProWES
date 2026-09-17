"""Pipe entity for the Flappy Bird game."""

from typing import final


@final
class Pipe:
    """A pipe object in the Flappy Bird game.
    
    Pipes have a horizontal position, vertical gap, width, and a passed flag.
    They can be moved horizontally and their right edge computed.
    """
    
    def __init__(
        self,
        x: float,
        gap_y: float,
        width: float,
        gap_height: float,
        passed: bool = False
    ) -> None:
        """Initialize a pipe with given properties.
        
        Args:
            x: The x-coordinate of the pipe's left edge.
            gap_y: The y-coordinate of the center of the pipe's gap.
            width: The width of the pipe.
            gap_height: The height of the pipe's gap.
            passed: Whether the pipe has been passed by the bird.
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
        """Move the pipe horizontally by subtracting speed from its x-coordinate.
        
        This method modifies the pipe's x attribute in-place.
        
        Args:
            speed: The speed to move the pipe (positive value).
        """
        self.x -= speed