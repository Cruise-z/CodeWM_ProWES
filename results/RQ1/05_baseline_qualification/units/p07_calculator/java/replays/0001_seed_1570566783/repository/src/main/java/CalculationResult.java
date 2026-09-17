/**
 * Data transfer object encapsulating the result of a calculation.
 * Either represents a successful computation with a numeric result,
 * or an error with a descriptive message.
 */
public class CalculationResult {
    /** Flag indicating whether the calculation was successful */
    private final boolean success;
    
    /** The numeric result if the calculation was successful, otherwise null */
    private final Double result;
    
    /** Error message if the calculation failed, otherwise null */
    private final String errorMessage;

    /**
     * Constructs a new CalculationResult representing a successful calculation.
     *
     * @param result the numeric result of the calculation
     */
    public CalculationResult(double result) {
        this.success = true;
        this.result = result;
        this.errorMessage = null;
    }

    /**
     * Constructs a new CalculationResult representing a failed calculation.
     *
     * @param errorMessage the error message describing why the calculation failed
     */
    public CalculationResult(String errorMessage) {
        this.success = false;
        this.result = null;
        this.errorMessage = errorMessage;
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
    public double getResult() {
        if (!success) {
            throw new IllegalStateException("Cannot get result from failed calculation");
        }
        return result;
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