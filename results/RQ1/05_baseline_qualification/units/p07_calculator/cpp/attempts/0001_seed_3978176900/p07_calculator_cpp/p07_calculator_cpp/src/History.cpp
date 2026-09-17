#include "History.h"

namespace calc {

void History::record(const std::string& expr, double value) {
    HistoryEntry entry;
    entry.expression = expr;
    entry.result = value;
    historyEntries_.push_back(entry);
}

const std::vector<HistoryEntry>& History::entries() const {
    return historyEntries_;
}

void History::clear() {
    historyEntries_.clear();
}

} // namespace calc