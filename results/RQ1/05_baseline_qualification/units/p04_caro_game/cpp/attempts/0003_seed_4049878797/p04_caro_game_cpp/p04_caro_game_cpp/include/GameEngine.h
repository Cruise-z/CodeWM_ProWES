#ifndef GAME_ENGINE_H
#define GAME_ENGINE_H

#include <memory>
#include "Board.h"
#include "MoveHistory.h"
#include "WinDetector.h"

namespace FiveInARow {

/**
 * @brief Orchestrates the game logic including move application, turn alternation, and game status updates
 */
class GameEngine {
private:
    Board board;              ///< The game board
    Player current;           ///< The player whose turn it currently is
    GameStatus status;        ///< The current status of the game
    MoveHistory history;      ///< Records all moves made in the game

public:
    /**
     * @brief Construct a new GameEngine object
     * @param w Width of the board (default: 15)
     * @param h Height of the board (default: 15)
     */
    explicit GameEngine(size_t w = 15, size_t h = 15);

    /**
     * @brief Get a const reference to the game board
     * @return const Board& Reference to the game board
     */
    const Board& getBoard() const noexcept;

    /**
     * @brief Get the current player
     * @return Player The player whose turn it currently is
     */
    Player getCurrentPlayer() const noexcept;

    /**
     * @brief Get the current game status
     * @return GameStatus The current game status
     */
    GameStatus getStatus() const noexcept;

    /**
     * @brief Get a const reference to the move history
     * @return const MoveHistory& Reference to the move history
     */
    const MoveHistory& getHistory() const noexcept;

    /**
     * @brief Apply a move for the current player at the specified coordinates
     * @param r Row coordinate
     * @param c Column coordinate
     * @return MoveError Error code indicating success or failure of the move
     */
    MoveError applyMove(size_t r, size_t c);

    /**
     * @brief Reset the game to its initial state
     */
    void reset();
};

} // namespace FiveInARow

#endif // GAME_ENGINE_H