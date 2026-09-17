#ifndef CALCULATOR_EVALUATOR_H
#define CALCULATOR_EVALUATOR_H

#include <string>
#include <vector>
#include "Tokens.h"

namespace calc {

struct EvalResult {
    bool success;
    double value;
    std::string errorMessage;
    size_t errorPosition;
};

class Evaluator {
public:
    EvalResult evaluateRPN(const std::vector<Token>& rpn) const;
};

} // namespace calc

#endif // CALCULATOR_EVALUATOR_H