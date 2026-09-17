import java.util.*;

/**
 * Represents the snake in the game, maintaining its body as an ordered sequence of positions.
 */
public final class Snake {
    /** The body of the snake, stored as a deque with head at the front. */
    private final Deque<Position> body;

    /**
     * Creates a new snake with a single segment at the given starting position.
     *
     * @param start the initial position of the snake's head
     * @throws NullPointerException if start is null
     */
    public Snake(Position start) {
        Objects.requireNonNull(start, "Start position cannot be null");
        this.body = new ArrayDeque<>();
        this.body.addFirst(start);
    }

    /**
     * Returns the current head position of the snake.
     *
     * @return the head position
     */
    public Position head() {
        return body.getFirst();
    }

    /**
     * Returns the current tail position of the snake.
     *
     * @return the tail position
     */
    public Position tail() {
        return body.getLast();
    }

    /**
     * Returns the length of the snake in segments.
     *
     * @return the number of segments in the snake
     */
    public int length() {
        return body.size();
    }

    /**
     * Checks if the snake occupies the given position.
     *
     * @param p the position to check
     * @return true if any segment of the snake occupies the position, false otherwise
     * @throws NullPointerException if p is null
     */
    public boolean occupies(Position p) {
        Objects.requireNonNull(p, "Position cannot be null");
        return body.contains(p);
    }

    /**
     * Moves the snake to a new head position, removing the tail segment.
     * This simulates the snake moving one cell forward.
     *
     * @param nextHead the new head position
     * @throws NullPointerException if nextHead is null
     */
    public void moveTo(Position nextHead) {
        Objects.requireNonNull(nextHead, "Next head position cannot be null");
        body.addFirst(nextHead);
        body.removeLast();
    }

    /**
     * Grows the snake by adding a new head segment while keeping the tail.
     * This simulates the snake eating food and growing longer.
     *
     * @param nextHead the new head position
     * @throws NullPointerException if nextHead is null
     */
    public void growTo(Position nextHead) {
        Objects.requireNonNull(nextHead, "Next head position cannot be null");
        body.addFirst(nextHead);
    }

    /**
     * Returns a defensive copy of the snake's body as a list, ordered from head to tail.
     *
     * @return an unmodifiable list of positions representing the snake's body
     */
    public List<Position> bodyAsList() {
        return Collections.unmodifiableList(new ArrayList<>(body));
    }
}