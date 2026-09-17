/**
 * Interface for random number generation abstraction.
 * This interface allows injecting different randomness sources,
 * making the system testable with deterministic behavior.
 */
public interface RandomSource {
    /**
     * Generates a random integer between 0 (inclusive) and the specified bound (exclusive).
     *
     * @param bound the upper bound (exclusive), must be positive
     * @return a random integer in the range [0, bound)
     * @throws IllegalArgumentException if bound is not positive
     */
    int nextInt(int bound);
}