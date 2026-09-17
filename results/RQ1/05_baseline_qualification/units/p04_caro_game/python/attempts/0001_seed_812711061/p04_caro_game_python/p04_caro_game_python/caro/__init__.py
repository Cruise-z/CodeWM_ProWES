"""Public API for the Caro game implementation.

This module exports all necessary classes and exceptions to interact with
the Caro game engine. It serves as the primary interface for users of the
caro package, providing access to game state, moves, and error handling.
"""

from .game import CaroGame
from .types import Player, Status
from .move import Move
from .errors import InvalidMoveError, GameOverError

# Expose the public API
__all__ = [
    "CaroGame",
    "Player",
    "Status",
    "Move",
    "InvalidMoveError",
    "GameOverError",
]