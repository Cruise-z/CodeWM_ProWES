#include "Calculator.h"
#include "Lexer.h"
#include "Parser.h"
#include "Evaluator.h"

namespace calc {

Calculator::Calculator() = default;

EvaluationOutcome Calculator::evaluate(const std::string& expression) {
    // Tokenize the input expression
    Lexer lexer;
    LexResult lexResult = lexer.tokenize(expression);
    
    if (!lexResult.success) {
        return {false, 0.0, lexResult.errorMessage, lexResult.errorPosition};
    }
    
    // Parse tokens into RPN
    Parser parser;
    ParseResult parseResult = parser.toRPN(lexResult.tokens);
    
    if (!parseResult.success) {
        return {false, 0.0, parseResult.errorMessage, parseResult.errorPosition};
    }
    
    // Evaluate the RPN expression
    Evaluator evaluator;
    EvalResult evalResult = evaluator.evaluateRPN(parseResult.rpn);
    
    if (!evalResult.success) {
        return {false, 0.0, evalResult.errorMessage, evalResult.errorPosition};
    }
    
    // Record successful evaluation in history
    history_.record(expression, evalResult.value);
    
    return {true, evalResult.value, "", 0};
}

const std::vector<HistoryEntry>& Calculator::history() const {
    return history_.entries();
}

void Calculator::clearHistory() {
    history_.clear();
}

} // namespace calc