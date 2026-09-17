"""Enumerations for Player and Status in the Caro game."""

from enum import Enum


class Player(Enum):
    """Enumeration of players in the Caro game."""
    X = 'X'
    O = 'O'


class Status(Enum):
    """Enumeration of game statuses."""
    IN_PROGRESS = 'IN_PROGRESS'
    X_WON = 'X_WON'
    O_WON = 'O_WON'
    DRAW = 'DRAW'