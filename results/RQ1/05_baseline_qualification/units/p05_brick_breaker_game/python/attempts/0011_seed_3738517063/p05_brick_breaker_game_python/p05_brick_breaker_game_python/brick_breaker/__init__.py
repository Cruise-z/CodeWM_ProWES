"""Public API for the brick breaker game.

This module exposes the main classes and functions needed to use the brick breaker game.
"""

from .config import GameConfig
from .game import Game

# Explicitly expose the main classes for the public API
__all__ = ['GameConfig', 'Game']