/**
 * Implementation of RandomSource using java.util.Random.
 * This class provides deterministic random number generation based on a seed.
 */
public final class JavaUtilRandomSource implements RandomSource {
    /** The underlying random number generator. */
    private final java.util.Random rnd;

    /**
     * Constructs a new JavaUtilRandomSource with the specified seed.
     *
     * @param seed the seed for the random number generator
     */
    public JavaUtilRandomSource(long seed) {
        this.rnd = new java.util.Random(seed);
    }

    /**
     * Generates a random integer between 0 (inclusive) and the specified bound (exclusive).
     *
     * @param bound the upper bound (exclusive), must be positive
     * @return a random integer in the range [0, bound)
     * @throws IllegalArgumentException if bound is not positive
     */
    @Override
    public int nextInt(int bound) {
        if (bound <= 0) {
            throw new IllegalArgumentException("Bound must be positive");
        }
        return rnd.nextInt(bound);
    }
}