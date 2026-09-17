#ifndef CALCULATOR_HISTORY_H
#define CALCULATOR_HISTORY_H

#include <string>
#include <vector>

namespace calc {

struct HistoryEntry {
    std::string expression;
    double result;
};

class History {
public:
    void record(const std::string& expr, double value);
    const std::vector<HistoryEntry>& entries() const;
    void clear();

private:
    std::vector<HistoryEntry> historyEntries_;
};

} // namespace calc

#endif // CALCULATOR_HISTORY_H