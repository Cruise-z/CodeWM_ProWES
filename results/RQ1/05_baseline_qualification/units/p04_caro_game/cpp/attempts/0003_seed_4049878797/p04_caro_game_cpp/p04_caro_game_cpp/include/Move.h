#ifndef MOVE_H
#define MOVE_H

#include "Common.h"

namespace FiveInARow {

/**
 * @brief Represents a move in the game with row, column, and player
 */
struct Move {
    size_t row;    ///< Row coordinate of the move
    size_t col;    ///< Column coordinate of the move
    Player player; ///< Player who made the move

    /**
     * @brief Construct a new Move object
     * @param r Row coordinate
     * @param c Column coordinate
     * @param p Player who made the move
     */
    Move(size_t r, size_t c, Player p) : row(r), col(c), player(p) {}

    /**
     * @brief Check if two moves are equal
     * @param other Move to compare with
     * @return bool True if moves are equal, false otherwise
     */
    bool operator==(const Move& other) const noexcept;
};

} // namespace FiveInARow

#endif // MOVE_H