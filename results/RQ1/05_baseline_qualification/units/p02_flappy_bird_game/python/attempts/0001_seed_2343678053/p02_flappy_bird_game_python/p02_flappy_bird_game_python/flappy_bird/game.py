"""Game orchestration module for the Flappy Bird implementation."""

from typing import List, Tuple, final

from flappy_bird.config import Config
from flappy_bird.physics import integrate_vy
from flappy_bird.scoring import is_pipe_scored
from flappy_bird.collision import hits_bounds, hits_pipe
from flappy_bird.pipes import Pipe


@final
class Game:
    """Orchestration layer for the Flappy Bird game state machine.
    
    Manages game state, bird physics, pipe lifecycle, scoring, and collisions.
    """
    
    def __init__(self, config: Config, initial_pipes: List[Pipe] = None) -> None:
        """Initialize the game with a configuration and optional initial pipes.
        
        Args:
            config: Configuration parameters for the game.
            initial_pipes: Optional list of pipes to start with.
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
        """Apply a flap action to the bird.
        
        In 'ready' state, transitions to 'running' and applies flap impulse.
        In 'running' state, reapplies the flap impulse.
        In 'game_over' state, does nothing.
        """
        if self._state == "game_over":
            return
        
        # Apply flap impulse (always downward velocity)
        impulse = self._config.flap_impulse
        self._bird_vy = impulse
        
        # Transition to running state if currently ready
        if self._state == "ready":
            self._state = "running"
    
    def step(self) -> None:
        """Advance the game state by one tick.
        
        Executes the deterministic sequence of operations:
        1. Integrate vertical velocity with gravity
        2. Update bird position
        3. Move pipes
        4. Score pipes (if applicable)
        5. Check collisions
        6. Remove off-screen pipes
        """
        # If not running, just advance tick
        if self._state != "running":
            self._tick += 1
            return
        
        # 1. Integrate vertical velocity with gravity
        self._bird_vy = integrate_vy(
            self._bird_vy, self._config.gravity, self._config.max_vy
        )
        
        # 2. Update bird position
        self._bird_y += self._bird_vy
        
        # 3. Move pipes
        for pipe in self._pipes:
            pipe.step(self._config.pipe_speed)
        
        # 4. Score pipes
        # Iterate backwards to safely remove items during iteration
        for pipe in reversed(self._pipes):
            if not pipe.passed:
                right_edge = pipe.right_edge()
                if is_pipe_scored(self._config.bird_x, right_edge, pipe.passed):
                    pipe.passed = True
                    self._score += 1
        
        # 5. Check collisions
        bird_hits_bounds = hits_bounds(
            self._bird_y, self._config.world_ceiling, self._config.world_floor
        )
        
        bird_hits_pipe = any(
            hits_pipe(self._config.bird_x, self._bird_y, pipe)
            for pipe in self._pipes
        )
        
        if bird_hits_bounds or bird_hits_pipe:
            self._state = "game_over"
        
        # 6. Remove off-screen pipes (after scoring)
        self._pipes = [
            pipe for pipe in self._pipes
            if pipe.right_edge() >= 0
        ]
        
        # 7. Increment tick
        self._tick += 1
    
    def pipes_readonly(self) -> Tuple[Pipe, ...]:
        """Get an immutable snapshot of the current pipes.
        
        Includes pipes that have been passed until they are removed off-screen.
        
        Returns:
            A tuple of Pipe objects representing the current state of pipes.
        """
        return tuple(self._pipes)
    
    def status(self) -> dict:
        """Get a dictionary representation of the current game state.
        
        Returns:
            A dictionary containing:
            - state: Current game state ('ready', 'running', 'game_over')
            - tick: Current tick count
            - y: Bird's vertical position
            - vy: Bird's vertical velocity
            - score: Current score
            - pipes: List of dictionaries describing each pipe
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