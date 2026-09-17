#include "Parser.h"
#include "Tokens.h"
#include <stack>
#include <stdexcept>

namespace calc {

ParseResult Parser::toRPN(const std::vector<Token>& tokens) const {
    std::vector<Token> output;
    std::stack<Token> operatorStack;
    
    for (const auto& token : tokens) {
        if (token.type == TokenType::NUMBER) {
            output.push_back(token);
        } else if (token.type == TokenType::LEFT_PAREN) {
            operatorStack.push(token);
        } else if (token.type == TokenType::RIGHT_PAREN) {
            while (!operatorStack.empty() && 
                   operatorStack.top().type != TokenType::LEFT_PAREN) {
                output.push_back(operatorStack.top());
                operatorStack.pop();
            }
            
            if (operatorStack.empty()) {
                return {false, {}, "Mismatched parentheses", token.position};
            }
            
            operatorStack.pop(); // Remove the left parenthesis
        } else if (token.type == TokenType::OPERATOR) {
            while (!operatorStack.empty() &&
                   operatorStack.top().type == TokenType::OPERATOR &&
                   (precedence(operatorStack.top().op) > precedence(token.op) ||
                    (precedence(operatorStack.top().op) == precedence(token.op) &&
                     isLeftAssociative(token.op)))) {
                output.push_back(operatorStack.top());
                operatorStack.pop();
            }
            operatorStack.push(token);
        }
    }
    
    while (!operatorStack.empty()) {
        if (operatorStack.top().type == TokenType::LEFT_PAREN ||
            operatorStack.top().type == TokenType::RIGHT_PAREN) {
            return {false, {}, "Mismatched parentheses", operatorStack.top().position};
        }
        output.push_back(operatorStack.top());
        operatorStack.pop();
    }
    
    return {true, output, "", 0};
}

} // namespace calc