#include <cassert>
#include <string>
#include "Calculator.h"

int main() {
    calc::Calculator calculator;
    
    // Test 1: Basic precedence
    {
        auto outcome = calculator.evaluate("1+2*3");
        assert(outcome.success);
        assert(outcome.value == 7.0); // Should be 1 + (2*3) = 7
    }
    
    // Test 2: Parentheses override precedence
    {
        auto outcome = calculator.evaluate("(1+2)*3");
        assert(outcome.success);
        assert(outcome.value == 9.0); // Should be (1+2)*3 = 9
    }
    
    // Test 3: Division by zero
    {
        auto outcome = calculator.evaluate("1/0");
        assert(!outcome.success);
        assert(!outcome.errorMessage.empty());
    }
    
    // Test 4: History records only successful evaluations
    {
        auto outcome1 = calculator.evaluate("5+5");
        assert(outcome1.success);
        assert(outcome1.value == 10.0);
        
        auto outcome2 = calculator.evaluate("1/0");
        assert(!outcome2.success);
        
        auto outcome3 = calculator.evaluate("2*3");
        assert(outcome3.success);
        assert(outcome3.value == 6.0);
        
        const auto& history = calculator.history();
        assert(history.size() == 2); // Only successful evaluations
        
        assert(history[0].expression == "5+5");
        assert(history[0].result == 10.0);
        
        assert(history[1].expression == "2*3");
        assert(history[1].result == 6.0);
    }
    
    return 0;
}