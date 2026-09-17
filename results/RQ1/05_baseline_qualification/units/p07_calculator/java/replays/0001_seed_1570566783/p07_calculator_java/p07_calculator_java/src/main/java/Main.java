/**
 * Thin demo entrypoint for the calculator.
 * Instantiates a Calculator, evaluates a few expressions,
 * prints results and bounded history, then exits.
 */
public class Main {
    public static void main(String[] args) {
        // Create a calculator with history capacity of 3
        Calculator calc = new Calculator(3);
        
        // Test expressions
        String[] expressions = {
            "-3 + 4*2/(1-5)",
            "10 / 2",
            "1/0",
            "(2 + 3) * 4",
            "invalid expression"
        };
        
        // Evaluate each expression
        for (String expr : expressions) {
            System.out.println("Evaluating: " + expr);
            CalculationResult result = calc.evaluate(expr);
            
            if (result.isSuccess()) {
                System.out.println("Result: " + result.getResult());
            } else {
                System.out.println("Error: " + result.getErrorMessage());
            }
            System.out.println();
        }
        
        // Print history
        System.out.println("Calculation History:");
        for (HistoryEntry entry : calc.history()) {
            System.out.println("  Expression: " + entry.getExpression());
            if (entry.isSuccess()) {
                System.out.println("  Result: " + entry.getNumericResult());
            } else {
                System.out.println("  Error: " + entry.getErrorMessage());
            }
            System.out.println();
        }
        
        // Clear history and show that it's empty
        calc.clearHistory();
        System.out.println("After clearing history:");
        System.out.println("History size: " + calc.history().size());
    }
}