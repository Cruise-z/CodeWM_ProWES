#ifndef GOMOKU_MOVE_H
#define GOMOKU_MOVE_H

#include "Common.h"

namespace gomoku {

/**
 * @brief Represents a move in the game
 * 
 * A Move consists of a row index, column index, and the player making the move.
 */
struct Move {
    size_t row;     ///< Row index of the move
    size_t col;     ///< Column index of the move
    Player player;  ///< Player who made the move

    /**
     * @brief Construct a new Move object
     * 
     * @param r Row index
     * @param c Column index
     * @param p Player who made the move
     */
    Move(size_t r, size_t c, Player p);

    /**
     * @brief Compare two moves for equality
     * 
     * @param other The other move to compare with
     * @return true If both moves have the same row, column, and player
     * @return false Otherwise
     */
    bool operator==(const Move& other) const noexcept;
};

}  // namespace gomoku

#endif // GOMOKU_MOVE_H