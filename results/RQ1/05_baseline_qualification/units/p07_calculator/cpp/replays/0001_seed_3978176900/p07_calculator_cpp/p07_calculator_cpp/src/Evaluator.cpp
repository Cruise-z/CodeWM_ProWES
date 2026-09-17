#include "Evaluator.h"
#include "Tokens.h"
#include <stack>
#include <stdexcept>
#include <cmath>

namespace calc {

EvalResult Evaluator::evaluateRPN(const std::vector<Token>& rpn) const {
    std::stack<double> operandStack;
    
    for (const auto& token : rpn) {
        if (token.type == TokenType::NUMBER) {
            operandStack.push(token.numberValue);
        } else if (token.type == TokenType::OPERATOR) {
            // Check if we have enough operands
            if (operandStack.size() < 2) {
                return {false, 0.0, "Insufficient operands for operator", token.position};
            }
            
            // Pop two operands (note: order matters for non-commutative operators)
            double b = operandStack.top();
            operandStack.pop();
            double a = operandStack.top();
            operandStack.pop();
            
            double result = 0.0;
            switch (token.op) {
                case '+':
                    result = a + b;
                    break;
                case '-':
                    result = a - b;
                    break;
                case '*':
                    result = a * b;
                    break;
                case '/':
                    if (std::abs(b) < 1e-10) { // Check for division by zero
                        return {false, 0.0, "Division by zero", token.position};
                    }
                    result = a / b;
                    break;
                default:
                    return {false, 0.0, "Invalid operator in RPN", token.position};
            }
            
            operandStack.push(result);
        }
        // Parentheses tokens should not appear in RPN
    }
    
    // After processing all tokens, there should be exactly one value left
    if (operandStack.size() != 1) {
        return {false, 0.0, "Invalid expression: too many operands or missing operators", 0};
    }
    
    return {true, operandStack.top(), "", 0};
}

} // namespace calc