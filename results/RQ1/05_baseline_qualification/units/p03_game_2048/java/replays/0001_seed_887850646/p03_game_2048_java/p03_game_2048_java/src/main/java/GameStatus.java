/**
 * Enumeration representing the possible states of the 2048 game.
 */
public enum GameStatus {
    /**
     * The game is currently in progress.
     */
    IN_PROGRESS,
    
    /**
     * The player has won the game by reaching a tile with value 2048 or higher.
     */
    WON,
    
    /**
     * The game is over because no more moves are possible.
     */
    LOST
}