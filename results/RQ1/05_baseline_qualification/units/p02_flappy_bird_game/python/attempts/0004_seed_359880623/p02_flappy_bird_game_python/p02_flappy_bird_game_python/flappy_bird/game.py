"""Game orchestration module for the Flappy Bird game."""

from typing import List, Tuple, Dict, Any
from flappy_bird.config import Config
from flappy_bird.physics import integrate_vy
from flappy_bird.scoring import is_pipe_scored
from flappy_bird.collision import hits_bounds, hits_pipe
from flappy_bird.pipes import Pipe


class Game:
    """Orchestration of the Flappy Bird game state machine and rules."""

    def __init__(self, config: Config, initial_pipes: List[Pipe] = None) -> None:
        """Initialize the game with a configuration and optional initial pipes.

        Args:
            config: Configuration parameters for the game.
            initial_pipes: Optional list of pipes to start with.
        """
        self._config = config
        self._state = "ready"  # 'ready', 'running', or 'game_over'
        self._bird_y = config.start_y
        self._bird_vy = 0.0
        self._tick = 0
        self._score = 0
        self._pipes = initial_pipes.copy() if initial_pipes else []

    def reset(self) -> None:
        """Reset the game to its initial state."""
        self._state = "ready"
        self._bird_y = self._config.start_y
        self._bird_vy = 0.0
        self._tick = 0
        self._score = 0
        self._pipes.clear()

    def flap(self) -> None:
        """Apply a flap impulse to the bird.

        In 'ready' state, sets state to 'running' and applies the flap impulse.
        In 'running' state, re-applies the flap impulse.
        In 'game_over' state, does nothing.
        """
        if self._state == "game_over":
            return
        elif self._state == "ready":
            self._state = "running"
        
        # Apply the flap impulse (negative because upward is negative y)
        self._bird_vy = self._config.flap_impulse

    def step(self) -> None:
        """Advance the game by one time step.

        Processes physics, pipe movement, scoring, and collision checks
        in a deterministic order while in the 'running' state.
        """
        if self._state != "running":
            self._tick += 1
            return

        # 1) Update vertical velocity with gravity and clamp
        self._bird_vy = integrate_vy(
            self._bird_vy, self._config.gravity, self._config.max_vy
        )

        # 2) Update bird position
        self._bird_y += self._bird_vy

        # 3) Move all pipes to the left
        for pipe in self._pipes:
            pipe.step(self._config.pipe_speed)

        # 4) Score pipes that are now passed
        # Iterate in reverse to avoid issues with list mutation during iteration
        for i in reversed(range(len(self._pipes))):
            pipe = self._pipes[i]
            if not pipe.passed:
                right_edge = pipe.right_edge()
                if is_pipe_scored(self._config.bird_x, right_edge, pipe.passed):
                    pipe.passed = True
                    self._score += 1

        # 5) Check for collisions
        # Check collision with bounds
        if hits_bounds(self._bird_y, self._config.world_ceiling, self._config.world_floor):
            self._state = "game_over"
        else:
            # Check collision with pipes
            for pipe in self._pipes:
                if hits_pipe(self._config.bird_x, self._bird_y, pipe):
                    self._state = "game_over"
                    break

        # 6) Remove off-screen pipes after scoring
        # Iterate in reverse to avoid issues with list mutation during iteration
        for i in reversed(range(len(self._pipes))):
            pipe = self._pipes[i]
            if pipe.right_edge() < 0:
                self._pipes.pop(i)

        # 7) Increment tick counter
        self._tick += 1

    def pipes_readonly(self) -> Tuple[Pipe, ...]:
        """Get an immutable snapshot of the current pipes.

        Includes pipes that have been passed but not yet removed off-screen.

        Returns:
            A tuple containing copies of all current pipes.
        """
        return tuple(self._pipes)

    def status(self) -> Dict[str, Any]:
        """Get a snapshot of the current game state for reporting or testing.

        Returns:
            A dictionary with keys:
            - 'state': current game state ('ready', 'running', 'game_over')
            - 'tick': current tick count
            - 'y': bird's y position
            - 'vy': bird's vertical velocity
            - 'score': current score
            - 'pipes': list of dictionaries representing pipes
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