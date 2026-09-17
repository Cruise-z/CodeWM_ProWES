"""Public API re-exports for the Flappy Bird game."""

from .config import Config
from .pipes import Pipe
from .game import Game
from .scoring import is_pipe_scored

__all__ = ["Game", "Pipe", "Config", "is_pipe_scored"]