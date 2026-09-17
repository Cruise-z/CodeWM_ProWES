"""Game orchestration for the Flappy Bird game."""

from typing import List, Tuple, Dict, Any
from flappy_bird.config import Config
from flappy_bird.physics import integrate_vy, clamp
from flappy_bird.scoring import is_pipe_scored
from flappy_bird.collision import hits_bounds, hits_pipe
from flappy_bird.pipes import Pipe


class Game:
    """Orchestration of the Flappy Bird game state machine and rules."""

    def __init__(self, config: Config, initial_pipes: List[Pipe] = None) -> None:
        """Initialize the game with a configuration and optional initial pipes.

        Args:
            config: Configuration parameters for the game.
            initial_pipes: Optional list of initial pipes to start with.
        """
        self._config = config
        self._state = "ready"  # 'ready', 'running', 'game_over'
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
        """Apply a flap impulse to the bird's vertical velocity.

        In 'ready' state, transitions to 'running' and applies the flap impulse.
        In 'running' state, reapplies the flap impulse.
        In 'game_over' state, does nothing.
        """
        if self._state == "game_over":
            return
        
        # Transition to 'running' state on first flap from 'ready'
        if self._state == "ready":
            self._state = "running"
        
        # Apply the flap impulse (negative because positive y is down)
        self._bird_vy = self._config.flap_impulse

    def step(self) -> None:
        """Advance the game state by one tick.

        Applies physics, updates positions, handles collisions, scoring,
        and pipe management in a deterministic order.
        """
        if self._state != "running":
            self._tick += 1
            return

        # 1. Integrate vertical velocity with gravity and clamp
        self._bird_vy = integrate_vy(self._bird_vy, self._config.gravity, self._config.max_vy)

        # 2. Update bird's vertical position
        self._bird_y += self._bird_vy

        # 3. Move all pipes to the left
        for pipe in self._pipes:
            pipe.step(self._config.pipe_speed)

        # 4. Score pipes that are now passed
        for pipe in self._pipes:
            if not pipe.passed:
                right_edge = pipe.right_edge()
                if is_pipe_scored(self._config.bird_x, right_edge, pipe.passed):
                    pipe.passed = True
                    self._score += 1

        # 5. Check for collisions
        bird_x = self._config.bird_x
        if hits_bounds(self._bird_y, self._config.world_ceiling, self._config.world_floor):
            self._state = "game_over"
        else:
            for pipe in self._pipes:
                if hits_pipe(bird_x, self._bird_y, pipe):
                    self._state = "game_over"
                    break

        # 6. Remove off-screen pipes
        self._pipes = [pipe for pipe in self._pipes if pipe.right_edge() >= 0]

        # 7. Increment tick count
        self._tick += 1

    def pipes_readonly(self) -> Tuple[Pipe, ...]:
        """Return an immutable snapshot of the current pipes.

        Includes pipes that have been passed until they are fully off-screen.
        
        Returns:
            A tuple of Pipe objects representing the current state of pipes.
        """
        return tuple(self._pipes)

    def status(self) -> Dict[str, Any]:
        """Get a snapshot of the current game state for debugging or testing.

        Returns:
            A dictionary containing:
                - state: The current game state ('ready', 'running', or 'game_over')
                - tick: The current tick count
                - y: The bird's current y position
                - vy: The bird's current vertical velocity
                - score: The current score
                - pipes: A list of dictionaries describing each pipe's state
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
                    "passed": pipe.passed
                }
                for pipe in self._pipes
            ]
        }