#ifndef CALCULATOR_TOKENS_H
#define CALCULATOR_TOKENS_H

#include <cstddef>
#include <string>

namespace calc {

enum class TokenType {
    NUMBER,
    OPERATOR,
    LEFT_PAREN,
    RIGHT_PAREN
};

struct Token {
    TokenType type;
    double numberValue;
    char op;
    size_t position;
};

// Helper functions for operator precedence and associativity
int precedence(char op);
bool isLeftAssociative(char op);
bool isOperatorChar(char ch);

} // namespace calc

#endif // CALCULATOR_TOKENS_H