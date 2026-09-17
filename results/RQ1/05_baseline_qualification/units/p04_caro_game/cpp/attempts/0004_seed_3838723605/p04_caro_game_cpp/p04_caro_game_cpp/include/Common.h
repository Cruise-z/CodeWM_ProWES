#ifndef COMMON_H
#define COMMON_H

namespace FiveInARow {

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
    None,           ///< No error, move was successful
    OutOfBounds,    ///< Move coordinates are outside the board
    Occupied,       ///< Target cell is already occupied
    NotYourTurn,    ///< It's not the current player's turn
    GameOver        ///< Game has already ended
};

}  // namespace FiveInARow

#endif // COMMON_H