"""Configuration parameters and validation for the Flappy Bird game."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Config:
    """Configuration parameters for the Flappy Bird game.

    All parameters are immutable and validated upon creation.
    """

    # Physics constants
    gravity: float = 0.5
    flap_impulse: float = -7.5
    max_vy: float = 10.0

    # Bird properties
    bird_x: float = 100.0
    start_y: float = 200.0

    # Pipe properties
    pipe_speed: float = 3.0
    pipe_width: float = 50.0
    gap_height: float = 150.0
    spawn_interval_ticks: int = 150

    # World boundaries
    world_height: float = 600.0
    world_ceiling: float = 0.0
    world_floor: float = 550.0

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        # Validate world boundaries
        if self.world_ceiling >= self.world_floor:
            raise ValueError(
                "World ceiling must be less than world floor"
            )

        # Validate gap height
        if self.gap_height <= 0:
            raise ValueError("Gap height must be positive")

        # Validate pipe properties
        if self.pipe_width <= 0:
            raise ValueError("Pipe width must be positive")
        if self.spawn_interval_ticks < 1:
            raise ValueError("Spawn interval must be at least 1 tick")

        # Validate physics parameters
        if self.max_vy <= 0:
            raise ValueError("Max vertical velocity must be positive")