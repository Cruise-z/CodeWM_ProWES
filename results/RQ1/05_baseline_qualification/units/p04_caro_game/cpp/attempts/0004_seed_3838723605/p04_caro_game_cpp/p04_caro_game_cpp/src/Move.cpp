#include "Move.h"

namespace FiveInARow {

Move::Move(size_t r, size_t c, Player p) : row(r), col(c), player(p) {}

bool Move::operator==(const Move& other) const noexcept {
    return row == other.row && col == other.col && player == other.player;
}

}  // namespace FiveInARow