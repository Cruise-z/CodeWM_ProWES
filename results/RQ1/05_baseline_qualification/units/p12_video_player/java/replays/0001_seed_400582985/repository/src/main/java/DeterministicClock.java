/**
 * A deterministic, in-memory clock for testing purposes.
 * This clock does not rely on system time or any external timing mechanisms.
 */
public final class DeterministicClock {
    private long currentTimeMillis;

    /**
     * Constructs a new DeterministicClock with the initial time set to 0.
     */
    public DeterministicClock() {
        this.currentTimeMillis = 0L;
    }

    /**
     * Gets the current time in milliseconds.
     *
     * @return the current time in milliseconds
     */
    public long getCurrentTimeMillis() {
        return currentTimeMillis;
    }

    /**
     * Advances the clock by the specified number of milliseconds.
     * Throws IllegalArgumentException if deltaMillis is negative.
     *
     * @param deltaMillis the amount of time to advance in milliseconds (must be non-negative)
     * @throws IllegalArgumentException if deltaMillis is negative
     */
    public void advance(long deltaMillis) {
        if (deltaMillis < 0) {
            throw new IllegalArgumentException("Delta must not be negative");
        }
        this.currentTimeMillis += deltaMillis;
    }
}