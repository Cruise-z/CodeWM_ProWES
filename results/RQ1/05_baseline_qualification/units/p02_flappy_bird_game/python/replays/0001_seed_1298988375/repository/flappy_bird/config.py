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

    # World dimensions
    world_height: float = 500.0
    world_ceiling: float = 0.0
    world_floor: float = 500.0

    # Spawning and timing
    spawn_interval_ticks: int = 100

    def __post_init__(self) -> None:
        """Validate configuration parameters after initialization."""
        if self.world_ceiling >= self.world_floor:
            raise ValueError(
                "World ceiling must be less than world floor"
            )
        if self.gap_height <= 0:
            raise ValueError("Gap height must be positive")
        if self.pipe_width <= 0:
            raise ValueError("Pipe width must be positive")
        if self.max_vy <= 0:
            raise ValueError("Max vertical velocity must be positive")
        if self.spawn_interval_ticks < 1:
            raise ValueError("Spawn interval must be at least 1 tick")

    @property
    def world_bounds(self) -> tuple[float, float]:
        """Return the world bounds as (ceiling, floor)."""
        return (self.world_ceiling, self.world_floor)