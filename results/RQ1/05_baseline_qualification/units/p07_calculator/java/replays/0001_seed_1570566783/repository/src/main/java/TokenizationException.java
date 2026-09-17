/**
 * Specific exception for tokenization errors.
 * Thrown when the tokenizer encounters invalid characters or malformed numbers.
 */
public class TokenizationException extends CalculatorException {
    /**
     * Constructs a new TokenizationException with the specified detail message.
     *
     * @param message the detail message
     */
    public TokenizationException(String message) {
        super(message);
    }
}