#ifndef CALCULATOR_CALCULATOR_H
#define CALCULATOR_CALCULATOR_H

#include <string>
#include <vector>
#include "History.h"

namespace calc {

struct EvaluationOutcome {
    bool success;
    double value;
    std::string errorMessage;
    size_t errorPosition;
};

class Calculator {
public:
    Calculator();
    
    EvaluationOutcome evaluate(const std::string& expression);
    const std::vector<HistoryEntry>& history() const;
    void clearHistory();

private:
    History history_;
};

} // namespace calc

#endif // CALCULATOR_CALCULATOR_H