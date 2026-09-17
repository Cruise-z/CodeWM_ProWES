#ifndef GOMOKU_GAME_ENGINE_H
#define GOMOKU_GAME_ENGINE_H

#include <memory>
#include "Board.h"
#include "MoveHistory.h"
#include "WinDetector.h"

namespace gomoku {

/**
 * @brief Orchestrates the game logic for Gomoku
 * 
 * This class manages the core game state including the board,
 * current player, game status, and move history. It provides
 * methods to apply moves, check game status, and reset the game.
 */
class GameEngine {
private:
    Board board_;           ///< The game board
    Player current_;        ///< The player whose turn it is
    GameStatus status_;     ///< Current game status
    MoveHistory history_;   ///< History of all moves made

public:
    /**
     * @brief Construct a new GameEngine object
     * 
     * @param w Width of the board (default: 15)
     * @param h Height of the board (default: 15)
     */
    explicit GameEngine(size_t w = 15, size_t h = 15);

    /**
     * @brief Get a constant reference to the game board
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
     * @brief Get a constant reference to the move history
     * 
     * @return const MoveHistory& Reference to the move history
     */
    const MoveHistory& getHistory() const noexcept;

    /**
     * @brief Apply a move for the current player
     * 
     * This method validates the move, applies it to the board,
     * checks for win/draw conditions, and updates the game state.
     * 
     * @param r Row index of the move
     * @param c Column index of the move
     * @return MoveError Error code indicating success or failure
     */
    MoveError applyMove(size_t r, size_t c);

    /**
     * @brief Reset the game to its initial state
     * 
     * This clears the board, resets the move history, sets the game status
     * to InProgress, and makes Player::X the current player.
     */
    void reset();
};

}  // namespace gomoku

#endif // GOMOKU_GAME_ENGINE_H