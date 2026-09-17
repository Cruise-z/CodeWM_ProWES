"""Enumeration types for the 2048 game."""

from enum import Enum, auto


class Direction(Enum):
    """Direction enum for 2048 game moves."""
    LEFT = auto()
    RIGHT = auto()
    UP = auto()
    DOWN = auto()


class GameStatus(Enum):
    """Game status enum for 2048 game."""
    RUNNING = auto()
    WON = auto()
    LOST = auto()