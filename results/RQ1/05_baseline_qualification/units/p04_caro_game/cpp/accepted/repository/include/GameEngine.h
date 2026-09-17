#ifndef GOMOKU_GAME_ENGINE_H
#define GOMOKU_GAME_ENGINE_H

#include <cstddef>
#include "Board.h"
#include "MoveHistory.h"
#include "WinDetector.h"
#include "Common.h"

namespace gomoku {

/**
 * @brief Orchestrates the Gomoku game logic
 * 
 * The GameEngine class manages the game state, including the board,
 * current player, game status, and move history. It handles applying
 * moves, enforcing turn alternation, and detecting game end conditions.
 */
class GameEngine {
private:
    Board board_;              ///< The game board
    Player current_;           ///< The player whose turn it is
    GameStatus status_;        ///< Current game status
    MoveHistory history_;      ///< History of all moves made

public:
    /**
     * @brief Construct a new GameEngine object
     * 
     * @param w Width of the board (default: 15)
     * @param h Height of the board (default: 15)
     */
    explicit GameEngine(size_t w = 15, size_t h = 15);

    /**
     * @brief Get a const reference to the game board
     * 
     * @return const Board& Reference to the game board
     */
    const Board& getBoard() const noexcept;

    /**
     * @brief Get the current player
     * 
     * @return Player Current player (Player::X or Player::O)
     */
    Player getCurrentPlayer() const noexcept;

    /**
     * @brief Get the current game status
     * 
     * @return GameStatus Current game status
     */
    GameStatus getStatus() const noexcept;

    /**
     * @brief Get a const reference to the move history
     * 
     * @return const MoveHistory& Reference to the move history
     */
    const MoveHistory& getHistory() const noexcept;

    /**
     * @brief Apply a move for the current player
     * 
     * This method validates the move, applies it to the board, updates
     * the game state, and checks for win/draw conditions.
     * 
     * @param r Row index of the move
     * @param c Column index of the move
     * @return MoveError Error code indicating success or failure
     */
    MoveError applyMove(size_t r, size_t c);

    /**
     * @brief Reset the game to its initial state
     * 
     * Clears the board, resets the move history, sets the game status
     * to InProgress, and makes Player::X the current player.
     */
    void reset();
};

} // namespace gomoku

#endif // GOMOKU_GAME_ENGINE_H