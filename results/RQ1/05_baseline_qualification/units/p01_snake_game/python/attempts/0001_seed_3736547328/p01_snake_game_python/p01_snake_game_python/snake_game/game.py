"""Game orchestration for the snake game."""

from __future__ import annotations

from typing import Dict, List, Tuple

from snake_game.direction import Direction
from snake_game.grid import Grid, Position
from snake_game.snake import Snake
from snake_game.collision import hit_wall, hit_self
from snake_game.food import place_food
from snake_game.random_provider import RandomProvider


class Game:
    """Orchestrates the snake game state and logic."""

    def __init__(
        self,
        grid: Grid,
        rng: RandomProvider,
        start: Position,
        direction: Direction,
    ) -> None:
        """Initialize a new game.

        Args:
            grid: The grid for the game.
            rng: The random provider for food placement.
            start: The initial position of the snake's head.
            direction: The initial direction of the snake.
        """
        self._grid = grid
        self._rng = rng
        self._snake = Snake(start, direction)
        # Place initial food not on the snake
        occupied = set(self._snake.body())
        self._food = place_food(grid, rng, occupied)
        self._score = 0
        self._over = False

    def turn(self, requested: Direction) -> bool:
        """Request a direction change for the snake.

        Args:
            requested: The requested direction to turn.

        Returns:
            True if the turn was accepted, False if it would cause immediate reversal.
        """
        return self._snake.turn(requested)

    def step(self) -> None:
        """Advance the game by one step.

        This method computes the next head position, checks for collisions,
        updates the snake's position, and handles food consumption and placement.
        """
        if self._over:
            return

        next_head = self._snake.next_head()
        grow = next_head == self._food

        # Check for collisions
        if hit_wall(self._grid, next_head) or hit_self(self._snake.body(), next_head, grow):
            self._over = True
            return

        # Advance the snake
        self._snake.advance(grow)

        if grow:
            # Increment score when food is eaten
            self._score += 1
            # Place new food after consumption
            occupied = set(self._snake.body())
            self._food = place_food(self._grid, self._rng, occupied)

    def reset(self) -> None:
        """Reset the game to its initial state."""
        self._snake = Snake(
            start=self._snake.head(),
            direction=self._snake._direction,
        )
        occupied = set(self._snake.body())
        self._food = place_food(self._grid, self._rng, occupied)
        self._score = 0
        self._over = False

    def state(self) -> Dict[str, object]:
        """Get the current game state as a dictionary.

        Returns:
            A dictionary containing the game state with keys:
            - width: int
            - height: int
            - snake: list[tuple[int, int]]
            - food: tuple[int, int]
            - score: int
            - over: bool
            - direction: str
        """
        return {
            "width": self._grid.width,
            "height": self._grid.height,
            "snake": [(pos.x, pos.y) for pos in self._snake.body()],
            "food": (self._food.x, self._food.y),
            "score": self._score,
            "over": self._over,
            "direction": self._snake._direction.name,
        }

    def is_over(self) -> bool:
        """Check if the game is over.

        Returns:
            True if the game is over, False otherwise.
        """
        return self._over

    def score_get(self) -> int:
        """Get the current score.

        Returns:
            The current score.
        """
        return self._score