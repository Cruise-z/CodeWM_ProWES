/**
 * Immutable class representing the result of a board move operation.
 * Contains information about whether the board state changed and how many points were scored.
 */
public final class MoveResult {
    private final boolean changed;
    private final int scoreGained;

    /**
     * Constructs a new MoveResult with the specified change status and score gain.
     *
     * @param changed   true if any cell on the board was modified by the move, false otherwise
     * @param scoreGained the total points earned from merging tiles during this move
     */
    public MoveResult(boolean changed, int scoreGained) {
        this.changed = changed;
        this.scoreGained = scoreGained;
    }

    /**
     * Returns whether the board state changed as a result of the move.
     *
     * @return true if any cell was modified, false otherwise
     */
    public boolean changed() {
        return changed;
    }

    /**
     * Returns the total score gained from merging tiles during this move.
     *
     * @return the points earned from merging tiles
     */
    public int scoreGained() {
        return scoreGained;
    }
}