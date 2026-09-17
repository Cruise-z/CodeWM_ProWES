#include <iostream>
#include <string>
#include "Calculator.h"

int main() {
    calc::Calculator calculator;
    
    // Test expressions
    std::vector<std::string> expressions = {
        "1 + 2 * 3",
        "(1 + 2) * 3",
        "10 / 2",
        "10 / 0",
        "((2 + 3) * 4) - 1"
    };
    
    for (const auto& expr : expressions) {
        auto outcome = calculator.evaluate(expr);
        std::cout << "Expression: " << expr << std::endl;
        if (outcome.success) {
            std::cout << "Result: " << outcome.value << std::endl;
        } else {
            std::cout << "Error: " << outcome.errorMessage 
                      << " at position " << outcome.errorPosition << std::endl;
        }
        std::cout << std::endl;
    }
    
    // Display history
    std::cout << "Calculation History:" << std::endl;
    const auto& hist = calculator.history();
    for (const auto& entry : hist) {
        std::cout << entry.expression << " = " << entry.result << std::endl;
    }
    
    return 0;
}