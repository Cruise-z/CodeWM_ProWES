#ifndef FIVEROW_GAMEENGINE_H
#define FIVEROW_GAMEENGINE_H

#include "Board.h"
#include "MoveHistory.h"
#include "WinDetector.h"
#include "Common.h"
#include <vector>

namespace fiverow {

/**
 * @brief Orchestrates the game logic, managing board state, moves, and game status
 */
class GameEngine {
private:
    Board board_;
    Player current_player_;
    GameStatus status_;
    MoveHistory history_;

public:
    /**
     * @brief Construct a new GameEngine object
     * @param w Width of the board (default: 15)
     * @param h Height of the board (default: 15)
     */
    explicit GameEngine(size_t w = 15, size_t h = 15);

    /**
     * @brief Get a const reference to the game board
     * @return const Board& Reference to the internal board
     */
    const Board& getBoard() const noexcept;

    /**
     * @brief Get the current player
     * @return Player Current player (X or O)
     */
    Player getCurrentPlayer() const noexcept;

    /**
     * @brief Get the current game status
     * @return GameStatus Current game status
     */
    GameStatus getStatus() const noexcept;

    /**
     * @brief Get a const reference to the move history
     * @return const MoveHistory& Reference to the internal move history
     */
    const MoveHistory& getHistory() const noexcept;

    /**
     * @brief Apply a move for the current player at given coordinates
     * @param r Row index
     * @param c Column index
     * @return MoveError Error code indicating success or failure
     */
    MoveError applyMove(size_t r, size_t c);

    /**
     * @brief Reset the game to its initial state
     */
    void reset();
};

}  // namespace fiverow

#endif // FIVEROW_GAMEENGINE_H