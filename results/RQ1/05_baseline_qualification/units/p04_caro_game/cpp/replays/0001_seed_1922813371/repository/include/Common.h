#ifndef GOMOKU_COMMON_H
#define GOMOKU_COMMON_H

namespace gomoku {

/// Represents a player in the game
enum class Player {
    X,  ///< Player X (Alice)
    O   ///< Player O (Eve)
};

/// Represents the state of a cell on the board
enum class CellState {
    Empty,  ///< Empty cell
    X,      ///< Cell occupied by Player X
    O       ///< Cell occupied by Player O
};

/// Represents the current status of the game
enum class GameStatus {
    InProgress,  ///< Game is ongoing
    WonX,        ///< Player X has won
    WonO,        ///< Player O has won
    Draw         ///< Game ended in a draw
};

/// Represents possible errors when applying a move
enum class MoveError {
    None,          ///< No error, move was successful
    OutOfBounds,   ///< Move coordinates are outside the board
    Occupied,      ///< Cell at move coordinates is already occupied
    NotYourTurn,   ///< Attempted to make a move out of turn
    GameOver       ///< Game has already ended
};

} // namespace gomoku

#endif // GOMOKU_COMMON_H