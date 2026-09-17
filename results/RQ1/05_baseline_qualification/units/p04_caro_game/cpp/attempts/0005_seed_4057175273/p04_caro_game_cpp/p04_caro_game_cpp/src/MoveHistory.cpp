#include "MoveHistory.h"

namespace gomoku {

void MoveHistory::push(const Move& m) {
    history.push_back(m);
}

bool MoveHistory::undo(Move& out) {
    if (history.empty()) {
        return false;
    }
    out = history.back();
    history.pop_back();
    return true;
}

const std::vector<Move>& MoveHistory::all() const noexcept {
    return history;
}

void MoveHistory::clear() noexcept {
    history.clear();
}

size_t MoveHistory::size() const noexcept {
    return history.size();
}

}  // namespace gomoku