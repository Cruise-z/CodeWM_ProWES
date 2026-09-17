/**
 * Specific exception for parse errors.
 * Thrown when the parser encounters syntax errors such as mismatched parentheses
 * or incomplete expressions.
 */
public class ParseException extends CalculatorException {
    /**
     * Constructs a new ParseException with the specified detail message.
     *
     * @param message the detail message
     */
    public ParseException(String message) {
        super(message);
    }
}