"""Exception types for Caro game validation and state management."""

class InvalidMoveError(Exception):
    """Raised when a move is invalid while the game is IN_PROGRESS.

    This includes moves that are out-of-bounds or attempt to occupy
    a cell that is already occupied.
    """

class GameOverError(Exception):
    """Raised when attempting to make a move after the game has ended.

    This occurs when trying to move after a win or draw has been detected.
    """