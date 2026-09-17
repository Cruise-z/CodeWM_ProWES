/**
 * Thin runtime entry: small demo using fully qualified java.util.Arrays.asList(...).
 */
public class Main {
    /**
     * Main entry point for the application.
     * Creates a small arena, tanks, engine; enqueues one or two commands;
     * ticks; prints single concise snapshot of tank ids and scores; exits.
     *
     * @param args command line arguments (ignored)
     */
    public static void main(String[] args) {
        // Create a small arena (6x5) with an obstacle at (2,2)
        ObstacleMap obstacles = ObstacleMap.empty();
        obstacles.add(new Position(2, 2));
        Arena arena = new Arena(6, 5, obstacles);

        // Create two tanks
        Tank alice = new Tank("Alice", new Position(1, 2), Orientation.EAST, 3);
        Tank bob = new Tank("Bob", new Position(4, 2), Orientation.WEST, 3);

        // Create game engine
        GameEngine engine = new GameEngine(arena, java.util.Arrays.asList(alice, bob));

        // Enqueue some commands
        engine.enqueue("Alice", Command.MOVE_FORWARD);
        engine.enqueue("Bob", Command.TURN_RIGHT);

        // Tick the game
        engine.tick();

        // Print a concise snapshot of tank IDs and scores
        System.out.println("Tank IDs and Scores:");
        for (String id : engine.getTanksCopy().keySet()) {
            Tank tank = engine.getTanksCopy().get(id);
            System.out.println(id + ": " + engine.getScoreBoardCopy().getScore(id));
        }
    }
}