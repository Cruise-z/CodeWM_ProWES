/**
 * Enum representing the possible outcomes of a game tick.
 */
public enum MoveOutcome {
    /** The snake moved to a new position without eating food. */
    MOVED,
    
    /** The snake moved and ate food, growing longer and increasing score. */
    ATE_FOOD,
    
    /** The snake collided with a wall or itself, ending the game. */
    GAME_OVER
}