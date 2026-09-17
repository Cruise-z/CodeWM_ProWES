#ifndef MOVE_HISTORY_H
#define MOVE_HISTORY_H

#include <vector>
#include "Move.h"

namespace FiveInARow {

/**
 * @brief Manages the history of moves in a game
 */
class MoveHistory {
private:
    std::vector<Move> history_;

public:
    /**
     * @brief Adds a move to the history
     * @param m The move to add
     */
    void push(const Move& m);

    /**
     * @brief Removes the last move from history and returns it
     * @param out The move that was removed
     * @return True if a move was successfully removed, false if history was empty
     */
    bool undo(Move& out);

    /**
     * @brief Gets all moves in history
     * @return Reference to vector of moves
     */
    const std::vector<Move>& all() const noexcept;

    /**
     * @brief Clears the move history
     */
    void clear() noexcept;

    /**
     * @brief Gets the number of moves in history
     * @return Number of moves
     */
    size_t size() const noexcept;
};

}  // namespace FiveInARow

#endif // MOVE_HISTORY_H