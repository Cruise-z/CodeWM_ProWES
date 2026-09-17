"""Public API for the brick breaker game.

This module exposes the core classes and functions needed to interact
with the brick breaker game implementation.
"""

from .config import GameConfig
from .game import Game

__all__ = ['GameConfig', 'Game']