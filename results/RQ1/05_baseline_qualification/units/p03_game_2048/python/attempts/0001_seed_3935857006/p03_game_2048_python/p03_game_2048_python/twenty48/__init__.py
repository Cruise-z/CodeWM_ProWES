"""Public API re-exports for the 2048 game package."""

from .board import Board
from .game import Game
from .types import Direction, GameStatus

__all__ = ['Board', 'Game', 'Direction', 'GameStatus']