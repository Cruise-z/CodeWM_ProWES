/**
 * Interface representing a deterministic source of tile spawns.
 * Implementations must provide a sequence of spawns that are consumed
 * exactly as specified by the game logic.
 */
public interface Spawner {
    /**
     * Returns the next spawn in the sequence.
     * This method must not return null.
     *
     * @return the next spawn to be placed on the board
     */
    Spawn nextSpawn();
}