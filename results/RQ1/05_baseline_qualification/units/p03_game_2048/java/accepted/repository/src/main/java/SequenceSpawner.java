/**
 * A deterministic spawner that consumes a predefined sequence of spawns.
 * The sequence is consumed in order, wrapping around to the beginning when exhausted.
 */
public final class SequenceSpawner implements Spawner {
    private final java.util.List<Spawn> sequence;
    private int index;

    /**
     * Constructs a SequenceSpawner with the given sequence of spawns.
     *
     * @param sequence the list of spawns to be consumed in order
     * @throws IllegalArgumentException if sequence is null
     */
    public SequenceSpawner(java.util.List<Spawn> sequence) {
        if (sequence == null) {
            throw new IllegalArgumentException("Sequence cannot be null");
        }
        this.sequence = sequence;
        this.index = 0;
    }

    /**
     * Returns the next spawn in the sequence.
     * If the end of the sequence is reached, it wraps around to the beginning.
     *
     * @return the next spawn to be placed on the board
     */
    @Override
    public Spawn nextSpawn() {
        if (sequence.isEmpty()) {
            throw new IllegalStateException("No spawns available in sequence");
        }
        Spawn spawn = sequence.get(index);
        index = (index + 1) % sequence.size();
        return spawn;
    }

    /**
     * Creates and returns a default SequenceSpawner with a documented sequence.
     * This sequence is used by the Main class for deterministic behavior.
     *
     * @return a SequenceSpawner with a predefined sequence of spawns
     */
    public static SequenceSpawner defaultSequence() {
        // Documented sequence for deterministic behavior:
        // Initial two spawns for reset()
        java.util.List<Spawn> sequence = new java.util.ArrayList<>();
        sequence.add(new Spawn(0, 0, 2)); // Row 0, Col 0, Value 2
        sequence.add(new Spawn(0, 1, 2)); // Row 0, Col 1, Value 2
        
        // Additional spawns for subsequent moves
        sequence.add(new Spawn(0, 2, 4)); // Row 0, Col 2, Value 4
        sequence.add(new Spawn(0, 3, 2)); // Row 0, Col 3, Value 2
        sequence.add(new Spawn(1, 0, 2)); // Row 1, Col 0, Value 2
        sequence.add(new Spawn(1, 1, 4)); // Row 1, Col 1, Value 4
        sequence.add(new Spawn(1, 2, 2)); // Row 1, Col 2, Value 2
        sequence.add(new Spawn(1, 3, 2)); // Row 1, Col 3, Value 2
        sequence.add(new Spawn(2, 0, 2)); // Row 2, Col 0, Value 2
        sequence.add(new Spawn(2, 1, 2)); // Row 2, Col 1, Value 2
        sequence.add(new Spawn(2, 2, 4)); // Row 2, Col 2, Value 4
        sequence.add(new Spawn(2, 3, 2)); // Row 2, Col 3, Value 2
        sequence.add(new Spawn(3, 0, 2)); // Row 3, Col 0, Value 2
        sequence.add(new Spawn(3, 1, 2)); // Row 3, Col 1, Value 2
        sequence.add(new Spawn(3, 2, 2)); // Row 3, Col 2, Value 2
        sequence.add(new Spawn(3, 3, 4)); // Row 3, Col 3, Value 4
        
        return new SequenceSpawner(sequence);
    }
}