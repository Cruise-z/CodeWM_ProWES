/**
 * Obstacle set with add/isBlocked/copy.
 */
public class ObstacleMap {
    private final java.util.Set<Position> obstacles;

    /**
     * Creates a new obstacle map with no obstacles.
     */
    public ObstacleMap() {
        this.obstacles = new java.util.HashSet<>();
    }

    /**
     * Creates a new obstacle map with the given obstacles.
     *
     * @param obstacles the set of obstacles
     */
    public ObstacleMap(java.util.Set<Position> obstacles) {
        this.obstacles = new java.util.HashSet<>(obstacles);
    }

    /**
     * Creates an empty obstacle map.
     *
     * @return a new empty obstacle map
     */
    public static ObstacleMap empty() {
        return new ObstacleMap();
    }

    /**
     * Adds an obstacle at the given position.
     *
     * @param p the position to add an obstacle
     */
    public void add(Position p) {
        obstacles.add(p);
    }

    /**
     * Checks if there is an obstacle at the given position.
     *
     * @param p the position to check
     * @return true if there is an obstacle at the position, false otherwise
     */
    public boolean isBlocked(Position p) {
        return obstacles.contains(p);
    }

    /**
     * Creates a copy of this obstacle map.
     *
     * @return a new obstacle map with the same obstacles
     */
    public ObstacleMap copy() {
        return new ObstacleMap(obstacles);
    }
}