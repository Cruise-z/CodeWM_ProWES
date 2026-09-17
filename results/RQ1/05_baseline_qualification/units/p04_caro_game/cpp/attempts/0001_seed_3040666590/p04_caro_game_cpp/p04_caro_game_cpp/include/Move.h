#ifndef FIVEROW_MOVE_H
#define FIVEROW_MOVE_H

#include "Common.h"

namespace fiverow {

/**
 * @brief Represents a move in the game with row, column, and player
 */
struct Move {
    size_t row;
    size_t col;
    Player player;

    /**
     * @brief Construct a new Move object
     * @param r Row index
     * @param c Column index
     * @param p Player making the move
     */
    Move(size_t r, size_t c, Player p) : row(r), col(c), player(p) {}

    /**
     * @brief Compare two moves for equality
     * @param other Another move to compare with
     * @return true if moves are equal, false otherwise
     */
    bool operator==(const Move& other) const noexcept {
        return row == other.row && col == other.col && player == other.player;
    }
};

}  // namespace fiverow

#endif // FIVEROW_MOVE_H