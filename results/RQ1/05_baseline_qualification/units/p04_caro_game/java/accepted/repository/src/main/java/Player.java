/**
 * Enum representing the players in the game.
 * X goes first and alternates with O.
 */
public enum Player {
    X,
    O;

    /**
     * Returns the next player in the sequence.
     * If this is X, returns O.
     * If this is O, returns X.
     *
     * @return the next player
     */
    public Player next() {
        return this == X ? O : X;
    }

    /**
     * Returns a string representation of the player.
     *
     * @return "X" for X, "O" for O
     */
    @Override
    public String toString() {
        return this == X ? "X" : "O";
    }
}