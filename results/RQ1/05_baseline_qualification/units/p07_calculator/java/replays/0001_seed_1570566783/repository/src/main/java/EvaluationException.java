/**
 * Specific exception for evaluation errors.
 * Thrown when the parser encounters arithmetic errors such as division by zero.
 */
public class EvaluationException extends CalculatorException {
    /**
     * Constructs a new EvaluationException with the specified detail message.
     *
     * @param message the detail message
     */
    public EvaluationException(String message) {
        super(message);
    }
}