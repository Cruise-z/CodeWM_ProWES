/**
 * Data transfer object capturing a single calculation entry in the history.
 * Contains the original expression, whether it was successful, 
 * the numeric result (if successful), and error message (if failed).
 */
public class HistoryEntry {
    /** The original arithmetic expression that was evaluated */
    private final String expression;
    
    /** Flag indicating whether the calculation was successful */
    private final boolean success;
    
    /** The numeric result if the calculation was successful, otherwise null */
    private final Double numericResult;
    
    /** Error message if the calculation failed, otherwise null */
    private final String errorMessage;

    /**
     * Constructs a new HistoryEntry for a successful calculation.
     *
     * @param expression the original arithmetic expression
     * @param numericResult the numeric result of the calculation
     */
    public HistoryEntry(String expression, double numericResult) {
        this.expression = expression;
        this.success = true;
        this.numericResult = numericResult;
        this.errorMessage = null;
    }

    /**
     * Constructs a new HistoryEntry for a failed calculation.
     *
     * @param expression the original arithmetic expression
     * @param errorMessage the error message describing why the calculation failed
     */
    public HistoryEntry(String expression, String errorMessage) {
        this.expression = expression;
        this.success = false;
        this.numericResult = null;
        this.errorMessage = errorMessage;
    }

    /**
     * Returns the original arithmetic expression that was evaluated.
     *
     * @return the expression string
     */
    public String getExpression() {
        return expression;
    }

    /**
     * Returns whether the calculation was successful.
     *
     * @return true if the calculation succeeded, false otherwise
     */
    public boolean isSuccess() {
        return success;
    }

    /**
     * Returns the numeric result of a successful calculation.
     * This method should only be called when {@link #isSuccess()} returns true.
     *
     * @return the numeric result
     * @throws IllegalStateException if the calculation was not successful
     */
    public Double getNumericResult() {
        if (!success) {
            throw new IllegalStateException("Cannot get numeric result from failed calculation");
        }
        return numericResult;
    }

    /**
     * Returns the error message for a failed calculation.
     * This method should only be called when {@link #isSuccess()} returns false.
     *
     * @return the error message
     * @throws IllegalStateException if the calculation was successful
     */
    public String getErrorMessage() {
        if (success) {
            throw new IllegalStateException("Cannot get error message from successful calculation");
        }
        return errorMessage;
    }
}