#include "Tokens.h"
#include <cctype>
#include <stdexcept>

namespace calc {

int precedence(char op) {
    switch (op) {
        case '+':
        case '-':
            return 1;
        case '*':
        case '/':
            return 2;
        default:
            throw std::invalid_argument("Invalid operator for precedence");
    }
}

bool isLeftAssociative(char op) {
    // All operators in this calculator are left associative
    return true;
}

bool isOperatorChar(char ch) {
    return ch == '+' || ch == '-' || ch == '*' || ch == '/';
}

} // namespace calc