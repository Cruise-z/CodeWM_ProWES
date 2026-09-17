/**
 * A boundary interface for random number generation.
 * This interface abstracts the source of randomness to allow for
 * deterministic testing and different implementations.
 */
public interface RandomSource {
    /**
     * Returns a uniformly distributed random integer in the range [0, bound).
     *
     * @param bound the upper bound (exclusive). Must be positive.
     * @return a random integer in the range [0, bound)
     * @throws IllegalArgumentException if bound is not positive
     */
    int nextInt(int bound);
}