#ifndef MOVE_H
#define MOVE_H

#include "Common.h"

namespace FiveInARow {

/**
 * @brief Represents a move in the game
 */
struct Move {
    size_t row;    ///< Row index of the move
    size_t col;    ///< Column index of the move
    Player player; ///< Player who made the move

    /**
     * @brief Constructs a new Move object
     * @param r Row index
     * @param c Column index
     * @param p Player who made the move
     */
    Move(size_t r, size_t c, Player p);

    /**
     * @brief Checks if two moves are equal
     * @param other The other move to compare with
     * @return True if moves are equal, false otherwise
     */
    bool operator==(const Move& other) const noexcept;
};

}  // namespace FiveInARow

#endif // MOVE_H