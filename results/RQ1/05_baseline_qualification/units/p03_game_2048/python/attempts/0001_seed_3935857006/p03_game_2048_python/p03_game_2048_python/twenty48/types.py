"""Enum definitions for 2048 game direction and game status."""

from enum import Enum, auto


class Direction(Enum):
    """Direction enum for 2048 game movements."""
    LEFT = auto()
    RIGHT = auto()
    UP = auto()
    DOWN = auto()


class GameStatus(Enum):
    """Game status enum for 2048 game states."""
    RUNNING = auto()
    WON = auto()
    LOST = auto()