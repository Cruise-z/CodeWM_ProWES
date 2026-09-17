/**
 * A deterministic random number generator adapter using java.util.Random.
 * This implementation is suitable for testing with fixed seeds.
 */
public final class JavaUtilRandomSource implements RandomSource {
    /** The underlying random number generator. */
    private final java.util.Random rnd;

    /**
     * Creates a new JavaUtilRandomSource with the specified seed.
     *
     * @param seed the seed value for the random number generator
     */
    public JavaUtilRandomSource(long seed) {
        this.rnd = new java.util.Random(seed);
    }

    /**
     * Returns a uniformly distributed random integer in the range [0, bound).
     *
     * @param bound the upper bound (exclusive). Must be positive.
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