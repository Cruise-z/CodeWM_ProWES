"""Public API for the brick breaker game.

This module exposes the core classes and functions needed to use the brick
breaker game library. It serves as the package's public interface.
"""

from .config import GameConfig
from .game import Game

# Explicitly export the main classes to make them available at package level
__all__ = ['GameConfig', 'Game']