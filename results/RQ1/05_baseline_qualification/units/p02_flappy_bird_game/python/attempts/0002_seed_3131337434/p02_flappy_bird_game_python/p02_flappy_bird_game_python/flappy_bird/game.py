"""Game orchestration module for the Flappy Bird game."""

from typing import List, Tuple, Dict, Any
from flappy_bird.config import Config
from flappy_bird.physics import integrate_vy
from flappy_bird.scoring import is_pipe_scored
from flappy_bird.collision import hits_bounds, hits_pipe
from flappy_bird.pipes import Pipe


class Game:
    """Orchestration of the Flappy Bird game state machine and rules.

    This class manages the game's state, bird physics, pipe management,
    scoring, and collision detection according to the specified rules.
    """

    def __init__(self, config: Config, initial_pipes: List[Pipe] = None) -> None:
        """Initialize the game with a configuration and optional starting pipes.

        Args:
            config: Game configuration parameters.
            initial_pipes: Optional list of pipes to start with.
        """
        self._config = config
        self._state = "ready"  # 'ready', 'running', or 'game_over'
        self._tick = 0
        self._score = 0
        self._bird_y = config.start_y
        self._bird_vy = 0.0
        self._pipes = initial_pipes.copy() if initial_pipes else []

    def reset(self) -> None:
        """Reset the game to its initial state."""
        self._state = "ready"
        self._tick = 0
        self._score = 0
        self._bird_y = self._config.start_y
        self._bird_vy = 0.0
        self._pipes.clear()

    def flap(self) -> None:
        """Apply a flap impulse to the bird.

        In 'ready' state, this transitions to 'running' and applies the impulse.
        In 'running' state, re-applies the impulse.
        In 'game_over' state, does nothing.
        """
        if self._state == "game_over":
            return
        
        # Set state to running on first flap from ready
        if self._state == "ready":
            self._state = "running"
        
        # Apply the flap impulse (negative because up is negative y)
        self._bird_vy = self._config.flap_impulse

    def step(self) -> None:
        """Advance the game by one time step.

        Applies physics, updates positions, handles collisions, scoring, and
        pipe lifecycle in a deterministic order.
        """
        if self._state != "running":
            self._tick += 1
            return

        # 1. Integrate vertical velocity with gravity and clamp
        self._bird_vy = integrate_vy(
            self._bird_vy, self._config.gravity, self._config.max_vy
        )

        # 2. Update bird position
        self._bird_y += self._bird_vy

        # 3. Move all pipes
        for pipe in self._pipes:
            pipe.step(self._config.pipe_speed)

        # 4. Score pipes
        for pipe in self._pipes:
            if not pipe.passed:
                right_edge = pipe.right_edge()
                if is_pipe_scored(
                    self._config.bird_x, right_edge, pipe.passed
                ):
                    pipe.passed = True
                    self._score += 1

        # 5. Check collisions
        if (
            hits_bounds(self._bird_y, self._config.world_ceiling, self._config.world_floor)
            or any(
                hits_pipe(self._config.bird_x, self._bird_y, pipe)
                for pipe in self._pipes
            )
        ):
            self._state = "game_over"

        # 6. Remove off-screen pipes (after scoring)
        self._pipes = [
            pipe for pipe in self._pipes if pipe.right_edge() >= 0
        ]

        # 7. Increment tick
        self._tick += 1

    def pipes_readonly(self) -> Tuple[Pipe, ...]:
        """Get an immutable snapshot of the current pipes.

        Includes pipes that have been passed and are still in the list
        until they are fully off-screen and removed.

        Returns:
            A tuple of Pipe objects representing the current state of pipes.
        """
        return tuple(self._pipes)

    def status(self) -> Dict[str, Any]:
        """Get a snapshot of the current game state.

        Returns:
            A dictionary containing:
            - state: Current game state ('ready', 'running', 'game_over')
            - tick: Current tick count
            - y: Bird's vertical position
            - vy: Bird's vertical velocity
            - score: Current score
            - pipes: List of pipe dictionaries with their properties
        """
        return {
            "state": self._state,
            "tick": self._tick,
            "y": self._bird_y,
            "vy": self._bird_vy,
            "score": self._score,
            "pipes": [
                {
                    "x": pipe.x,
                    "gap_y": pipe.gap_y,
                    "width": pipe.width,
                    "gap_height": pipe.gap_height,
                    "passed": pipe.passed,
                }
                for pipe in self._pipes
            ],
        }