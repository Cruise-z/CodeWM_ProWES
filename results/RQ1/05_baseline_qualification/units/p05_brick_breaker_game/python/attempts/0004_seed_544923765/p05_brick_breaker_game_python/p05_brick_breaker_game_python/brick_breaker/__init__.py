"""
Package initialization module for the brick breaker game.

This module exposes the public API of the brick breaker package,
re-exporting the core classes and functions needed by users.
"""

from .config import GameConfig
from .game import Game

__all__ = ["GameConfig", "Game"]