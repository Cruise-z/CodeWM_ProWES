/**
 * Interface for random number generation.
 * This abstraction allows injecting deterministic or seeded behavior for testing.
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