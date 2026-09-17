#include "MoveHistory.h"

namespace gomoku {

void MoveHistory::push(const Move& m) {
    history_.push_back(m);
}

bool MoveHistory::undo(Move& out) {
    if (history_.empty()) {
        return false;
    }
    out = history_.back();
    history_.pop_back();
    return true;
}

const std::vector<Move>& MoveHistory::all() const noexcept {
    return history_;
}

void MoveHistory::clear() noexcept {
    history_.clear();
}

size_t MoveHistory::size() const noexcept {
    return history_.size();
}

} // namespace gomoku