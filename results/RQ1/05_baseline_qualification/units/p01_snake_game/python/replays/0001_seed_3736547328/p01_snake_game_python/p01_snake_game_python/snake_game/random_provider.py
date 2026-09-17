"""Deterministic random provider for food placement."""

from __future__ import annotations

from typing import Optional, List
from snake_game.grid import Grid, Position


class RandomProvider:
    """A deterministic random provider that can use a pre-seeded sequence or LCG."""

    def __init__(self, sequence: Optional[List[Position]] = None, seed: Optional[int] = None) -> None:
        """Initialize the random provider with an optional sequence or seed.

        Args:
            sequence: An optional list of pre-seeded positions to use.
            seed: An optional seed for the LCG generator if no sequence is provided.
        """
        if sequence is not None:
            self._queue = sequence.copy()
        else:
            self._queue = []
        self._seed = seed if seed is not None else 42

    def next_position(self, grid: Grid) -> Position:
        """Generate the next position within the grid bounds.

        Args:
            grid: The grid to generate a position within.

        Returns:
            A Position object within the grid bounds.
        """
        if self._queue:
            # Use the queue if available
            return self._queue.pop(0)
        else:
            # Generate a deterministic position using LCG
            # Simple LCG constants
            a = 1664525
            c = 1013904223
            m = 2**32
            
            # Update seed
            self._seed = (a * self._seed + c) % m
            
            # Generate x and y coordinates
            x = self._seed % grid.width
            y = (self._seed // grid.width) % grid.height
            
            return Position(x, y)