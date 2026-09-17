/**
 * Seeded random number generator wrapper that preserves the original seed
 * and provides non-consuming seed() method.
 */
public class RNG {
    /** The internal random number generator */
    private final java.util.Random random;
    
    /** The original seed passed to the constructor */
    public final long originalSeed;

    /**
     * Creates a new RNG with the specified seed.
     *
     * @param seed the seed for the random number generator
     */
    public RNG(long seed) {
        this.originalSeed = seed;
        this.random = new java.util.Random(seed);
    }

    /**
     * Returns the original seed without consuming from the random stream.
     *
     * @return the original seed
     */
    public long seed() {
        return this.originalSeed;
    }

    /**
     * Returns the next pseudorandom, uniformly distributed double value
     * between 0.0 (inclusive) and 1.0 (exclusive).
     *
     * @return the next pseudorandom, uniformly distributed double value
     */
    public double nextDouble() {
        return this.random.nextDouble();
    }

    /**
     * Returns the next pseudorandom, uniformly distributed int value
     * between 0 (inclusive) and the specified bound (exclusive).
     *
     * @param bound the upper bound (exclusive)
     * @return the next pseudorandom, uniformly distributed int value
     */
    public int nextInt(int bound) {
        return this.random.nextInt(bound);
    }
}