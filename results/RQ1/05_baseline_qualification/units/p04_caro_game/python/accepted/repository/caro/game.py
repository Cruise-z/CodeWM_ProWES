"""Orchestration engine for the Caro game."""

from typing import List, Optional
from .board import Board
from .move import Move
from .types import Player, Status
from .errors import InvalidMoveError, GameOverError
from .rules import has_five_or_more


class CaroGame:
    """Engine that orchestrates the Caro game state transitions and validations."""

    def __init__(self, size: int = 15, first_player: Player = Player.X) -> None:
        """Initialize a new Caro game.

        Args:
            size: The dimension of the square board. Must be at least 1.
            first_player: The player who starts the game. Defaults to Player.X.
        """
        self._board = Board(size)
        self._current_player = first_player
        self._first_player = first_player
        self._status = Status.IN_PROGRESS
        self._winner: Optional[Player] = None
        self._history: List[Move] = []

    def move(self, row: int, col: int) -> None:
        """Make a move for the current player at the specified location.

        Validates the move according to the game rules and updates the game state.
        Raises exceptions if the move is invalid or the game has ended.

        Args:
            row: The row index where the player wants to place their stone.
            col: The column index where the player wants to place their stone.

        Raises:
            GameOverError: If the game has already ended (won or drawn).
            InvalidMoveError: If the move is out-of-bounds or the cell is occupied.
        """
        # 1) Check if the game has ended
        if self._status != Status.IN_PROGRESS:
            raise GameOverError()

        # 2) Check if the move is within bounds
        if not self._board.in_bounds(row, col):
            raise InvalidMoveError()

        # 3) Check if the cell is empty
        if not self._board.is_empty(row, col):
            raise InvalidMoveError()

        # All validations passed, make the move
        self._board.set_cell(row, col, self._current_player)
        move = Move(row, col, self._current_player)
        self._history.append(move)

        # Check for win
        if has_five_or_more(self._board, row, col, self._current_player):
            # Set the winner and update status
            self._status = Status.X_WON if self._current_player == Player.X else Status.O_WON
            self._winner = self._current_player
            # Do not toggle player since the game has ended
            return

        # Check for draw
        if self._board.is_full():
            self._status = Status.DRAW
            return

        # Game continues, toggle player
        self._current_player = Player.O if self._current_player == Player.X else Player.X

    def reset(self) -> None:
        """Reset the game to its initial state.

        Clears the board, history, and resets game state to the beginning.
        """
        self._board = Board()
        self._current_player = self._first_player
        self._status = Status.IN_PROGRESS
        self._winner = None
        self._history.clear()

    def board(self) -> List[List[Optional[Player]]]:
        """Get a snapshot of the current board state.

        Returns:
            A deep copy of the board's grid reflecting the current game state.
        """
        return self._board.to_matrix()

    def current_player(self) -> Player:
        """Get the player whose turn it currently is.

        Returns:
            The Player who is making the next move.
        """
        return self._current_player

    def status(self) -> Status:
        """Get the current status of the game.

        Returns:
            The current game status (IN_PROGRESS, X_WON, O_WON, or DRAW).
        """
        return self._status

    def winner(self) -> Optional[Player]:
        """Get the winner of the game if it has been won.

        Returns:
            The winning player if the game has been won, None otherwise.
        """
        return self._winner

    def history(self) -> List[Move]:
        """Get the history of moves made in the current game.

        Returns:
            A list of Move objects representing all moves made so far.
        """
        return self._history.copy()