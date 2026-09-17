#ifndef CALCULATOR_LEXER_H
#define CALCULATOR_LEXER_H

#include <string>
#include <vector>
#include "Tokens.h"

namespace calc {

struct LexResult {
    bool success;
    std::vector<Token> tokens;
    std::string errorMessage;
    size_t errorPosition;
};

class Lexer {
public:
    LexResult tokenize(const std::string& input) const;
};

} // namespace calc

#endif // CALCULATOR_LEXER_H