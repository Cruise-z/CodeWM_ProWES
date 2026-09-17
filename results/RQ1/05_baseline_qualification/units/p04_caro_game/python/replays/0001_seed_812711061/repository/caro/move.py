"""Immutable record for tracking moves in the Caro game."""

from dataclasses import dataclass
from .types import Player


@dataclass(frozen=True)
class Move:
    """Represents a move made by a player at a specific location on the board.

    This is an immutable record that captures the essential information about
    a move for history tracking purposes.
    """
    row: int
    col: int
    player: Player