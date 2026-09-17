#include "Move.h"

namespace fiverow {

// Implementation is minimal since Move is a simple struct with constructor and operator==
// All logic is already defined in the header file
Move::Move(size_t r, size_t c, Player p) : row(r), col(c), player(p) {}

bool Move::operator==(const Move& other) const noexcept {
    return row == other.row && col == other.col && player == other.player;
}

}  // namespace fiverow