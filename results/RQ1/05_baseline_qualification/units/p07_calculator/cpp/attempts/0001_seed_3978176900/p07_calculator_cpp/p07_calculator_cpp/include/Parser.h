#ifndef CALCULATOR_PARSER_H
#define CALCULATOR_PARSER_H

#include <string>
#include <vector>
#include "Tokens.h"

namespace calc {

struct ParseResult {
    bool success;
    std::vector<Token> rpn;
    std::string errorMessage;
    size_t errorPosition;
};

class Parser {
public:
    ParseResult toRPN(const std::vector<Token>& tokens) const;
};

} // namespace calc

#endif // CALCULATOR_PARSER_H