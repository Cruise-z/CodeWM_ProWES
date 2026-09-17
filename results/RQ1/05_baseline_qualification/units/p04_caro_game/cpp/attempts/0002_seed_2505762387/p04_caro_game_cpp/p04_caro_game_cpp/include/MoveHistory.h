#ifndef GOMOKU_MOVE_HISTORY_H
#define GOMOKU_MOVE_HISTORY_H

#include <vector>
#include "Move.h"

namespace gomoku {

/**
 * @brief Manages the history of moves in a game
 * 
 * This class stores all moves made during a game session,
 * allowing for operations like pushing new moves, undoing
 * the last move, and retrieving the complete move history.
 */
class MoveHistory {
private:
    std::vector<Move> history_;  ///< Storage for all moves in chronological order

public:
    /**
     * @brief Push a new move to the history
     * 
     * @param m The move to add to the history
     */
    void push(const Move& m);

    /**
     * @brief Undo the last move, removing it from history
     * 
     * @param out Reference to store the undone move
     * @return true If a move was successfully undone
     * @return false If the history is empty
     */
    bool undo(Move& out);

    /**
     * @brief Get reference to all moves in history
     * 
     * @return const std::vector<Move>& Reference to the internal move vector
     */
    const std::vector<Move>& all() const noexcept;

    /**
     * @brief Clear all moves from history
     */
    void clear() noexcept;

    /**
     * @brief Get the number of moves in history
     * 
     * @return size_t Number of moves stored
     */
    size_t size() const noexcept;
};

}  // namespace gomoku

#endif // GOMOKU_MOVE_HISTORY_H