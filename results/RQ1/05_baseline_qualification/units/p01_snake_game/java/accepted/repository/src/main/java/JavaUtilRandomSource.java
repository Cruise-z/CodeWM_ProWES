/**
 * Adapter implementation of RandomSource using java.util.Random.
 * This class provides a deterministic random number generator based on a seed.
 */
public final class JavaUtilRandomSource implements RandomSource {
    /** The underlying random number generator. */
    private final java.util.Random rnd;

    /**
     * Constructs a new JavaUtilRandomSource with the specified seed.
     *
     * @param seed the seed value for the random number generator
     */
    public JavaUtilRandomSource(long seed) {
        this.rnd = new java.util.Random(seed);
    }

    /**
     * Generates a uniformly distributed random integer in the range [0, bound).
     *
     * @param bound the upper bound (exclusive). Must be positive.
     * @return a random integer in [0, bound)
     * @throws IllegalArgumentException if bound <= 0
     */
    @Override
    public int nextInt(int bound) {
        if (bound <= 0) {
            throw new IllegalArgumentException("Bound must be positive");
        }
        return rnd.nextInt(bound);
    }
}