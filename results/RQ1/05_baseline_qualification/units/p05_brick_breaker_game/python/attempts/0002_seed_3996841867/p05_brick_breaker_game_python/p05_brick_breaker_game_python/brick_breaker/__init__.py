"""Public API for the brick breaker game package.

This module exposes the core classes and functions needed to use the
brick breaker game library. It serves as the main entry point for users
of the package.
"""

from .config import GameConfig
from .game import Game

__all__ = ["GameConfig", "Game"]