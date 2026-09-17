"""Public API re-exports for the Flappy Bird game."""

from flappy_bird.config import Config
from flappy_bird.pipes import Pipe
from flappy_bird.game import Game
from flappy_bird.scoring import is_pipe_scored

__all__ = ["Game", "Pipe", "Config", "is_pipe_scored"]