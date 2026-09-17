#include "Lexer.h"
#include "Tokens.h"
#include <cctype>
#include <stdexcept>

namespace calc {

LexResult Lexer::tokenize(const std::string& input) const {
    std::vector<Token> tokens;
    size_t position = 0;
    
    while (position < input.length()) {
        char ch = input[position];
        
        // Skip whitespace
        if (std::isspace(ch)) {
            position++;
            continue;
        }
        
        // Handle numbers
        if (std::isdigit(ch) || ch == '.') {
            size_t start = position;
            bool hasDecimal = false;
            
            while (position < input.length()) {
                char current = input[position];
                if (std::isdigit(current)) {
                    position++;
                } else if (current == '.' && !hasDecimal) {
                    hasDecimal = true;
                    position++;
                } else {
                    break;
                }
            }
            
            try {
                double numberValue = std::stod(input.substr(start, position - start));
                Token token;
                token.type = TokenType::NUMBER;
                token.numberValue = numberValue;
                token.position = start;
                tokens.push_back(token);
            } catch (const std::exception&) {
                return {false, {}, "Invalid number format", start};
            }
            continue;
        }
        
        // Handle operators and parentheses
        if (ch == '(') {
            Token token;
            token.type = TokenType::LEFT_PAREN;
            token.position = position;
            tokens.push_back(token);
            position++;
            continue;
        }
        
        if (ch == ')') {
            Token token;
            token.type = TokenType::RIGHT_PAREN;
            token.position = position;
            tokens.push_back(token);
            position++;
            continue;
        }
        
        if (isOperatorChar(ch)) {
            Token token;
            token.type = TokenType::OPERATOR;
            token.op = ch;
            token.position = position;
            tokens.push_back(token);
            position++;
            continue;
        }
        
        // Invalid character
        return {false, {}, "Invalid character", position};
    }
    
    return {true, tokens, "", 0};
}

} // namespace calc