#include "Move.h"

namespace FiveInARow {

bool Move::operator==(const Move& other) const noexcept {
    return row == other.row && col == other.col && player == other.player;
}

} // namespace FiveInARow