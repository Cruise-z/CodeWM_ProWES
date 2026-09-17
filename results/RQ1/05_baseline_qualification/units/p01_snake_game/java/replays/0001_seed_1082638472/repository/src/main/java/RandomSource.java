/**
 * Interface for random number generation.
 * This abstraction allows for deterministic testing by enabling injection
 * of controlled random sources.
 */
public interface RandomSource {
    /**
     * Generates a uniformly distributed random integer in the range [0, bound).
     *
     * @param bound the upper bound (exclusive). Must be positive.
     * @return a random integer in [0, bound)
     * @throws IllegalArgumentException if bound <= 0
     */
    int nextInt(int bound);
}