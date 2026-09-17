/**
 * Immutable record-like value representing a single move in the game.
 * Contains the position where the move was made, the player who made it,
 * and the index of the move in the game history.
 */
public final class Move {
    private final int row;
    private final int col;
    private final Player player;
    private final int index;

    /**
     * Creates a new Move instance.
     *
     * @param row   the row coordinate of the move
     * @param col   the column coordinate of the move
     * @param player the player who made the move
     * @param index the index of the move in the game history
     */
    public Move(int row, int col, Player player, int index) {
        this.row = row;
        this.col = col;
        this.player = player;
        this.index = index;
    }

    /**
     * Returns the row coordinate of the move.
     *
     * @return the row coordinate
     */
    public int getRow() {
        return row;
    }

    /**
     * Returns the column coordinate of the move.
     *
     * @return the column coordinate
     */
    public int getCol() {
        return col;
    }

    /**
     * Returns the player who made the move.
     *
     * @return the player
     */
    public Player getPlayer() {
        return player;
    }

    /**
     * Returns the index of the move in the game history.
     *
     * @return the move index
     */
    public int getIndex() {
        return index;
    }

    /**
     * Checks if this Move is equal to another object.
     *
     * @param o the object to compare with
     * @return true if the objects are equal, false otherwise
     */
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        Move move = (Move) o;

        if (row != move.row) return false;
        if (col != move.col) return false;
        if (index != move.index) return false;
        return player == move.player;
    }

    /**
     * Returns the hash code value for this Move.
     *
     * @return the hash code value
     */
    @Override
    public int hashCode() {
        int result = row;
        result = 31 * result + col;
        result = 31 * result + (player != null ? player.hashCode() : 0);
        result = 31 * result + index;
        return result;
    }

    /**
     * Returns a string representation of this Move.
     *
     * @return a string representation
     */
    @Override
    public String toString() {
        return "Move{" +
                "row=" + row +
                ", col=" + col +
                ", player=" + player +
                ", index=" + index +
                '}';
    }
}