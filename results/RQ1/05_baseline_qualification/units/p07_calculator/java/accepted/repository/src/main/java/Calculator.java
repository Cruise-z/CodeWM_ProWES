/**
 * Canonical public API for the calculator.
 * Coordinates Tokenizer and Parser, wraps outcomes into CalculationResult,
 * manages CalculationHistory bounded storage, and exposes history() and clearHistory().
 */
public class Calculator {
    /** The maximum capacity of the calculation history */
    private final int historyCapacity;
    
    /** The history store for calculations */
    private final CalculationHistory history;

    /**
     * Constructs a new Calculator with the default history capacity of 10.
     */
    public Calculator() {
        this(10);
    }

    /**
     * Constructs a new Calculator with the specified history capacity.
     *
     * @param historyCapacity the maximum number of entries to store in history
     */
    public Calculator(int historyCapacity) {
        this.historyCapacity = historyCapacity;
        this.history = new CalculationHistory(historyCapacity);
    }

    /**
     * Evaluates the given arithmetic expression.
     * 
     * @param expression the arithmetic expression to evaluate
     * @return a CalculationResult containing either the result or an error message
     */
    public CalculationResult evaluate(String expression) {
        try {
            // Tokenize the expression
            Tokenizer tokenizer = new Tokenizer(expression);
            java.util.List<Token> tokens = tokenizer.tokenize();
            
            // Parse and evaluate
            Parser parser = new Parser(tokens);
            double result = parser.evaluate();
            
            // Store in history
            HistoryEntry entry = new HistoryEntry(expression, result);
            history.add(entry);
            
            return new CalculationResult(result);
        } catch (CalculatorException e) {
            // Store in history
            HistoryEntry entry = new HistoryEntry(expression, e.getMessage());
            history.add(entry);
            
            return new CalculationResult(e.getMessage());
        }
    }

    /**
     * Returns the calculation history.
     * 
     * @return a list of HistoryEntry objects in insertion order
     */
    public java.util.List<HistoryEntry> history() {
        return history.getAll();
    }

    /**
     * Clears all entries from the calculation history.
     */
    public void clearHistory() {
        history.clear();
    }

    /**
     * Returns the maximum capacity of the calculation history.
     * 
     * @return the history capacity
     */
    public int historyCapacity() {
        return historyCapacity;
    }
}