"""Public API for the brick breaker game.

This module exposes the core classes and functions needed to use the brick
breaker game implementation. It provides a clean interface for creating
game instances and configuring gameplay parameters.
"""

from .config import GameConfig
from .game import Game

__all__ = ['GameConfig', 'Game']