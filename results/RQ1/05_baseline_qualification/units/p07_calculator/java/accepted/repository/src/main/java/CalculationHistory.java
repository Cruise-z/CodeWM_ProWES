/**
 * Bounded in-memory history store with insertion order retrieval.
 * Evicts oldest entries when capacity is exceeded.
 * Provides add, getAll, clear, capacity, and size operations.
 */
public class CalculationHistory {
    /** The maximum number of entries this history can hold */
    private final int capacity;
    
    /** The list storing history entries in insertion order */
    private java.util.List<HistoryEntry> entries;

    /**
     * Constructs a new CalculationHistory with the specified capacity.
     *
     * @param capacity the maximum number of entries to store
     */
    public CalculationHistory(int capacity) {
        this.capacity = capacity;
        this.entries = new java.util.ArrayList<>();
    }

    /**
     * Adds a new entry to the history.
     * If adding this entry exceeds the capacity, the oldest entry is removed.
     *
     * @param entry the history entry to add
     */
    public void add(HistoryEntry entry) {
        if (entries.size() >= capacity) {
            entries.remove(0); // Remove oldest entry
        }
        entries.add(entry);
    }

    /**
     * Returns all entries in the history in insertion order.
     *
     * @return a list of all history entries
     */
    public java.util.List<HistoryEntry> getAll() {
        return new java.util.ArrayList<>(entries);
    }

    /**
     * Clears all entries from the history.
     */
    public void clear() {
        entries.clear();
    }

    /**
     * Returns the maximum capacity of this history.
     *
     * @return the capacity
     */
    public int capacity() {
        return capacity;
    }

    /**
     * Returns the current number of entries in the history.
     *
     * @return the number of entries
     */
    public int size() {
        return entries.size();
    }
}