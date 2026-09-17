#ifndef FIVEROW_MOVEHISTORY_H
#define FIVEROW_MOVEHISTORY_H

#include <vector>
#include "Move.h"

namespace fiverow {

/**
 * @brief Manages the history of moves in a game
 */
class MoveHistory {
private:
    std::vector<Move> history_;

public:
    /**
     * @brief Push a move onto the history stack
     * @param m The move to add
     */
    void push(const Move& m);

    /**
     * @brief Undo the last move, returning it in the output parameter
     * @param out Reference to store the undone move
     * @return true if a move was undone, false if history was empty
     */
    bool undo(Move& out);

    /**
     * @brief Get reference to all moves in history
     * @return const std::vector<Move>& Reference to internal history vector
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

}  // namespace fiverow

#endif // FIVEROW_MOVEHISTORY_H