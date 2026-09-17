#ifndef GAME_ENGINE_H
#define GAME_ENGINE_H

#include <vector>
#include "Board.h"
#include "MoveHistory.h"
#include "WinDetector.h"

namespace FiveInARow {

/**
 * @brief Orchestrates the game logic for a Five in a Row game
 */
class GameEngine {
private:
    Board board_;              ///< The game board
    Player current_;           ///< The current player
    GameStatus status_;        ///< The current game status
    MoveHistory history_;      ///< History of moves in the game

public:
    /**
     * @brief Constructs a new GameEngine object
     * @param w Width of the board (default: 15)
     * @param h Height of the board (default: 15)
     */
    explicit GameEngine(size_t w = 15, size_t h = 15);

    /**
     * @brief Gets a constant reference to the game board
     * @return Constant reference to the board
     */
    const Board& getBoard() const noexcept;

    /**
     * @brief Gets the current player
     * @return Current player
     */
    Player getCurrentPlayer() const noexcept;

    /**
     * @brief Gets the current game status
     * @return Current game status
     */
    GameStatus getStatus() const noexcept;

    /**
     * @brief Gets a constant reference to the move history
     * @return Constant reference to the move history
     */
    const MoveHistory& getHistory() const noexcept;

    /**
     * @brief Applies a move for the current player at the specified coordinates
     * @param r Row index
     * @param c Column index
     * @return MoveError indicating success or failure reason
     */
    MoveError applyMove(size_t r, size_t c);

    /**
     * @brief Resets the game to its initial state
     */
    void reset();
};

}  // namespace FiveInARow

#endif // GAME_ENGINE_H