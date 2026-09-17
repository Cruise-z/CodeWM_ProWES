/**
 * Score tracking (hits, kills, score=h+5k), reset, asMap, copy.
 */
public class ScoreBoard {
    private final java.util.Map<String, Integer> hits;
    private final java.util.Map<String, Integer> kills;

    /**
     * Creates a new score board with the given tank IDs.
     * Initializes hits and kills to zero for each ID.
     *
     * @param ids the collection of tank IDs to track
     */
    public ScoreBoard(java.util.Collection<String> ids) {
        this.hits = new java.util.HashMap<>();
        this.kills = new java.util.HashMap<>();
        
        for (String id : ids) {
            hits.put(id, 0);
            kills.put(id, 0);
        }
    }

    /**
     * Adds a hit for the specified tank.
     *
     * @param id the tank ID
     */
    public void addHit(String id) {
        hits.put(id, hits.get(id) + 1);
    }

    /**
     * Adds a kill for the specified tank.
     *
     * @param id the tank ID
     */
    public void addKill(String id) {
        kills.put(id, kills.get(id) + 1);
    }

    /**
     * Gets the number of hits for the specified tank.
     *
     * @param id the tank ID
     * @return the number of hits
     */
    public int getHits(String id) {
        return hits.get(id);
    }

    /**
     * Gets the number of kills for the specified tank.
     *
     * @param id the tank ID
     * @return the number of kills
     */
    public int getKills(String id) {
        return kills.get(id);
    }

    /**
     * Gets the total score for the specified tank (hits + 5 * kills).
     *
     * @param id the tank ID
     * @return the total score
     */
    public int getScore(String id) {
        return hits.get(id) + 5 * kills.get(id);
    }

    /**
     * Returns a snapshot of the current scores as a map.
     *
     * @return a map of tank IDs to their scores
     */
    public java.util.Map<String, Integer> asMap() {
        java.util.Map<String, Integer> result = new java.util.HashMap<>();
        for (String id : hits.keySet()) {
            result.put(id, getScore(id));
        }
        return result;
    }

    /**
     * Creates a copy of this score board.
     *
     * @return a new score board with the same data
     */
    public ScoreBoard copy() {
        ScoreBoard copy = new ScoreBoard(hits.keySet());
        for (String id : hits.keySet()) {
            copy.hits.put(id, hits.get(id));
            copy.kills.put(id, kills.get(id));
        }
        return copy;
    }

    /**
     * Resets the score board for the given tank IDs.
     * Sets hits and kills to zero for each ID.
     *
     * @param tankIds the collection of tank IDs to reset
     */
    public void reset(java.util.Collection<String> tankIds) {
        for (String id : tankIds) {
            hits.put(id, 0);
            kills.put(id, 0);
        }
    }
}