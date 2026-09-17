/**
 * Specialization of EvaluationException for division by zero errors.
 * Thrown when the parser attempts to divide by zero during evaluation.
 */
public class DivisionByZeroException extends EvaluationException {
    /**
     * Constructs a new DivisionByZeroException with a default error message.
     */
    public DivisionByZeroException() {
        super("Division by zero");
    }
}