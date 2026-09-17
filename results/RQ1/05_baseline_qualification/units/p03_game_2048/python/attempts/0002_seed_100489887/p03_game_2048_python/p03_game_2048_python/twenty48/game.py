"""Game orchestration for the 2048 game."""

from random import Random
from typing import Optional
from .board import Board
from .types import Direction, GameStatus


class Game:
    """Orchestrates the 2048 game state and lifecycle."""

    def __init__(self, seed: int = 0) -> None:
        """
        Initialize the game with a deterministic random number generator.

        Args:
            seed: The seed for the random number generator.
        """
        self._rng: Random = Random(seed)
        self._board: Board = Board()
        self._score: int = 0
        self._status: GameStatus = GameStatus.RUNNING
        self.reset()

    def reset(self) -> None:
        """
        Reset the game state to initial conditions.

        This includes resetting the board to empty, setting score to 0,
        status to RUNNING, and spawning exactly two tiles.
        """
        self._board.reset_empty()
        self._score = 0
        self._status = GameStatus.RUNNING
        # Spawn two initial tiles
        self._board.add_random_tile(self._rng)
        self._board.add_random_tile(self._rng)

    def move(self, direction: Direction) -> bool:
        """
        Execute a move in the specified direction.

        Args:
            direction: The direction to move tiles.

        Returns:
            True if the move changed the board state, False otherwise.
        """
        if self._status != GameStatus.RUNNING:
            return False

        changed, gained_score = self._board.move(direction)
        if changed:
            self._score += gained_score
            if self._board.has_target():
                self._status = GameStatus.WON
            else:
                # Add a new tile after a successful move
                self._board.add_random_tile(self._rng)
                # Check if no more moves are possible
                if not self._board.can_move():
                    self._status = GameStatus.LOST

        return changed

    def get_status(self) -> GameStatus:
        """
        Get the current game status.

        Returns:
            The current GameStatus enum value.
        """
        return self._status

    def get_score(self) -> int:
        """
        Get the current score.

        Returns:
            The current score.
        """
        return self._score

    def get_board(self) -> Board:
        """
        Get the current board.

        Returns:
            The Board object representing the current game state.
        """
        return self._board