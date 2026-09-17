/**
 * Base checked exception for calculator internals.
 * All other calculator-specific exceptions extend this class.
 */
public class CalculatorException extends Exception {
    /**
     * Constructs a new CalculatorException with the specified detail message.
     *
     * @param message the detail message
     */
    public CalculatorException(String message) {
        super(message);
    }
}