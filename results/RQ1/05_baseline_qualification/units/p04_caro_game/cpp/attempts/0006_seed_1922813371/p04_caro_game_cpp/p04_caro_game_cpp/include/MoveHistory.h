#ifndef GOMOKU_MOVE_HISTORY_H
#define GOMOKU_MOVE_HISTORY_H

#include <vector>
#include "Move.h"

namespace gomoku {

/**
 * @brief Manages the history of moves in a game
 * 
 * The MoveHistory class stores all moves made during a game session,
 * allowing for move undoing, querying the move list, and clearing history.
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
     * @brief Undo the last move, returning it
     * 
     * @param out Reference to store the undone move
     * @return true if a move was successfully undone
     * @return false if history is empty
     */
    bool undo(Move& out);

    /**
     * @brief Get reference to all moves in history
     * 
     * @return const std::vector<Move>& Reference to the move history
     */
    const std::vector<Move>& all() const noexcept;

    /**
     * @brief Clear all moves from history
     */
    void clear() noexcept;

    /**
     * @brief Get the number of moves in history
     * 
     * @return size_t Number of moves recorded
     */
    size_t size() const noexcept;
};

} // namespace gomoku

#endif // GOMOKU_MOVE_HISTORY_H