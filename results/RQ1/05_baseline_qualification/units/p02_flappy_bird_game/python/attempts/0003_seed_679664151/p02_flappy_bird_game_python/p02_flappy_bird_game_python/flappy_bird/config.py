"""Configuration parameters and validation for the Flappy Bird game."""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class Config:
    """Configuration parameters for the Flappy Bird game.

    All parameters are immutable after creation.
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

    # World boundaries
    world_height: float = 500.0
    world_ceiling: float = 0.0
    world_floor: float = 500.0

    # Spawning and timing
    spawn_interval_ticks: int = 100

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        # Validate world boundaries
        if self.world_ceiling >= self.world_floor:
            raise ValueError(
                "world_ceiling must be less than world_floor"
            )
        if self.world_height != self.world_floor - self.world_ceiling:
            raise ValueError(
                "world_height must equal world_floor - world_ceiling"
            )

        # Validate pipe properties
        if self.pipe_width <= 0:
            raise ValueError("pipe_width must be positive")
        if self.gap_height <= 0:
            raise ValueError("gap_height must be positive")

        # Validate physics
        if self.max_vy <= 0:
            raise ValueError("max_vy must be positive")
        if self.spawn_interval_ticks < 1:
            raise ValueError("spawn_interval_ticks must be at least 1")

    @property
    def pipe_gap_y_low(self) -> float:
        """The lowest valid y-coordinate for a pipe's gap."""
        return self.world_ceiling + self.gap_height / 2

    @property
    def pipe_gap_y_high(self) -> float:
        """The highest valid y-coordinate for a pipe's gap."""
        return self.world_floor - self.gap_height / 2

    @classmethod
    def default(cls) -> "Config":
        """Create a default configuration."""
        return cls()