"""Configuration parameters and validation for the Flappy Bird game."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Configuration parameters for the Flappy Bird game.

    All parameters are immutable and validated upon instantiation.
    """

    # Physics constants
    gravity: float = 0.5
    flap_impulse: float = -7.5
    max_vy: float = 10.0

    # Bird properties
    bird_x: float = 100.0
    start_y: float = 250.0

    # Pipe properties
    pipe_speed: float = 3.0
    pipe_width: float = 50.0
    gap_height: float = 150.0
    spawn_interval_ticks: int = 150

    # World boundaries
    world_height: float = 500.0
    world_ceiling: float = 0.0
    world_floor: float = 500.0

    def __post_init__(self) -> None:
        """Validate configuration parameters after initialization."""
        if self.world_ceiling >= self.world_floor:
            raise ValueError(
                "world_ceiling must be less than world_floor"
            )
        if self.gap_height <= 0:
            raise ValueError("gap_height must be positive")
        if self.pipe_width <= 0:
            raise ValueError("pipe_width must be positive")
        if self.max_vy <= 0:
            raise ValueError("max_vy must be positive")
        if self.spawn_interval_ticks < 1:
            raise ValueError("spawn_interval_ticks must be at least 1")