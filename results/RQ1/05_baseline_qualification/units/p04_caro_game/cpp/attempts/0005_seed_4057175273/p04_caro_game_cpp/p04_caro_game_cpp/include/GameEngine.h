#ifndef GOMOKU_GAME_ENGINE_H
#define GOMOKU_GAME_ENGINE_H

#include <vector>
#include "Board.h"
#include "MoveHistory.h"
#include "WinDetector.h"

namespace gomoku {

/**
 * @brief Orchestrates the game logic for Gomoku
 * 
 * The GameEngine class manages the overall game state, including the board,
 * current player, game status, and move history. It provides methods for
 * applying moves, resetting the game, and retrieving game information.
 */
class GameEngine {
private:
    Board board;                    ///< The game board
    Player current;                 ///< The player whose turn it is
    GameStatus status;              ///< Current game status
    MoveHistory history;            ///< History of all moves made

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
     * @return GameStatus Current game status (InProgress, WonX, WonO, Draw)
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
     * This method validates the move coordinates, checks if the cell is empty,
     * applies the move to the board, and updates the game state accordingly.
     * It also handles turn alternation and win/draw detection.
     * 
     * @param r Row index of the move
     * @param c Column index of the move
     * @return MoveError Error code indicating success or failure of the move
     */
    MoveError applyMove(size_t r, size_t c);

    /**
     * @brief Reset the game to its initial state
     * 
     * This method clears the board, resets the move history, sets the game status
     * to InProgress, and makes Player::X the current player.
     */
    void reset();
};

}  // namespace gomoku

#endif // GOMOKU_GAME_ENGINE_H