"""Mutable snake implementation for the snake game."""

from __future__ import annotations

from typing import List

from snake_game.direction import Direction
from snake_game.grid import Position


class Snake:
    """A mutable snake with a body and direction."""

    def __init__(self, start: Position, direction: Direction) -> None:
        """Initialize a snake with a starting position and direction.

        Args:
            start: The initial position of the snake's head.
            direction: The initial direction of the snake.
        """
        self._body: List[Position] = [start]
        self._direction = direction

    def turn(self, requested: Direction) -> bool:
        """Attempt to change the snake's direction.

        Args:
            requested: The requested direction to turn.

        Returns:
            True if the turn was successful (not reversing), False otherwise.
        """
        if self._direction.is_opposite(requested):
            return False
        self._direction = requested
        return True

    def head(self) -> Position:
        """Get the current head position of the snake.

        Returns:
            The current head position.
        """
        return self._body[0]

    def next_head(self) -> Position:
        """Calculate the next head position based on current direction.

        Returns:
            The position that would be the next head position.
        """
        current_head = self.head()
        dx, dy = self._direction.delta()
        return Position(current_head.x + dx, current_head.y + dy)

    def advance(self, grow: bool) -> None:
        """Advance the snake by moving its head and optionally growing its body.

        Args:
            grow: If True, the snake grows by one segment; if False, it moves without growing.
        """
        next_head = self.next_head()
        self._body.insert(0, next_head)
        if not grow:
            self._body.pop()

    def body(self) -> List[Position]:
        """Get the current body of the snake.

        Returns:
            A list of positions representing the snake's body.
        """
        return self._body[:]