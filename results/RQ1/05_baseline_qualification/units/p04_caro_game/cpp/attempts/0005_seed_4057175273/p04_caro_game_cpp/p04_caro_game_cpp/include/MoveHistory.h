#ifndef GOMOKU_MOVE_HISTORY_H
#define GOMOKU_MOVE_HISTORY_H

#include <vector>
#include "Move.h"

namespace gomoku {

/**
 * @brief Manages the history of moves in a game
 * 
 * The MoveHistory class stores all moves made during a game session,
 * allowing for undo operations and maintaining a record of the game state.
 */
class MoveHistory {
private:
    std::vector<Move> history;  ///< Vector storing the sequence of moves

public:
    /**
     * @brief Push a move onto the history stack
     * 
     * @param m The move to add to the history
     */
    void push(const Move& m);

    /**
     * @brief Undo the last move, returning it to the caller
     * 
     * @param out Reference to a Move object where the undone move will be stored
     * @return true If a move was successfully undone
     * @return false If the history is empty (no moves to undo)
     */
    bool undo(Move& out);

    /**
     * @brief Get reference to the complete history of moves
     * 
     * @return const std::vector<Move>& Reference to the vector containing all moves
     */
    const std::vector<Move>& all() const noexcept;

    /**
     * @brief Clear the move history
     * 
     * This method removes all moves from the history, leaving it empty.
     */
    void clear() noexcept;

    /**
     * @brief Get the number of moves in the history
     * 
     * @return size_t Number of moves recorded in the history
     */
    size_t size() const noexcept;
};

}  // namespace gomoku

#endif // GOMOKU_MOVE_HISTORY_H