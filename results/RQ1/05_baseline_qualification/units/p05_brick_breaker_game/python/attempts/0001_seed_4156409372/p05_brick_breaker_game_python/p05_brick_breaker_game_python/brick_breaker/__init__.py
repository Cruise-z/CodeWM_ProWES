"""Public API for the brick breaker game.

This module exposes the main classes and functions for the brick breaker game.
It serves as the entry point for users of the package and re-exports the
necessary components from the internal modules.
"""

from .config import GameConfig
from .game import Game

__all__ = ["GameConfig", "Game"]