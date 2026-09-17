"""Public API for the brick breaker game package.

This module exports the core classes and functions that constitute the
public interface of the brick_breaker package.
"""

from .config import GameConfig
from .game import Game

__all__ = ["GameConfig", "Game"]