/**
 * Value type representing the state of the game.
 * Contains the status of the game and an optional winner.
 */
public final class GameState {
    /**
     * Enum representing the possible statuses of the game.
     */
    public enum Status {
        IN_PROGRESS,
        DRAW,
        X_WON,
        O_WON
    }

    private final Status status;
    private final java.util.Optional<Player> winner;

    /**
     * Private constructor for GameState.
     *
     * @param status the status of the game
     * @param winner the optional winner of the game
     */
    private GameState(Status status, java.util.Optional<Player> winner) {
        this.status = status;
        this.winner = winner;
    }

    /**
     * Returns a new GameState with status IN_PROGRESS and no winner.
     *
     * @return a new IN_PROGRESS GameState
     */
    public static GameState inProgress() {
        return new GameState(Status.IN_PROGRESS, java.util.Optional.empty());
    }

    /**
     * Returns a new GameState with status DRAW and no winner.
     *
     * @return a new DRAW GameState
     */
    public static GameState draw() {
        return new GameState(Status.DRAW, java.util.Optional.empty());
    }

    /**
     * Returns a new GameState with the specified player as winner.
     *
     * @param player the winning player
     * @return a new GameState with the specified player as winner
     */
    public static GameState won(Player player) {
        return new GameState(
            player == Player.X ? Status.X_WON : Status.O_WON,
            java.util.Optional.of(player)
        );
    }

    /**
     * Returns the status of the game.
     *
     * @return the game status
     */
    public Status getStatus() {
        return status;
    }

    /**
     * Returns the optional winner of the game.
     *
     * @return the winner, or empty if no winner exists
     */
    public java.util.Optional<Player> getWinner() {
        return winner;
    }

    /**
     * Returns a string representation of this GameState.
     *
     * @return a string representation
     */
    @Override
    public String toString() {
        return "GameState{" +
                "status=" + status +
                ", winner=" + winner +
                '}';
    }

    /**
     * Checks if this GameState is equal to another object.
     *
     * @param o the object to compare with
     * @return true if the objects are equal, false otherwise
     */
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        GameState gameState = (GameState) o;

        if (status != gameState.status) return false;
        return winner.equals(gameState.winner);
    }

    /**
     * Returns the hash code value for this GameState.
     *
     * @return the hash code value
     */
    @Override
    public int hashCode() {
        int result = status.hashCode();
        result = 31 * result + winner.hashCode();
        return result;
    }
}