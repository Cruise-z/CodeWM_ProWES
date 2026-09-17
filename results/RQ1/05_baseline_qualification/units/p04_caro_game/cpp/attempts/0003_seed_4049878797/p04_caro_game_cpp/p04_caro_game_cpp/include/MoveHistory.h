#ifndef MOVE_HISTORY_H
#define MOVE_HISTORY_H

#include <vector>
#include "Move.h"

namespace FiveInARow {

/**
 * @brief Manages the history of moves in the game
 */
class MoveHistory {
private:
    std::vector<Move> history;

public:
    /**
     * @brief Push a move onto the history stack
     * @param m The move to add to history
     */
    void push(const Move& m);

    /**
     * @brief Undo the last move, returning it via out parameter
     * @param out Reference to store the undone move
     * @return bool True if a move was undone, false if history was empty
     */
    bool undo(Move& out);

    /**
     * @brief Get reference to all moves in history
     * @return const std::vector<Move>& Reference to the move history vector
     */
    const std::vector<Move>& all() const noexcept;

    /**
     * @brief Clear all moves from history
     */
    void clear() noexcept;

    /**
     * @brief Get the number of moves in history
     * @return size_t Number of moves
     */
    size_t size() const noexcept;
};

} // namespace FiveInARow

#endif // MOVE_HISTORY_H