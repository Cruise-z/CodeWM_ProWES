import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;

/**
 * Represents the snake in the game, maintaining its body as an ordered sequence of positions.
 * The body is stored as a Deque where the head is at the front and the tail at the back.
 */
public final class Snake {
    /** The body of the snake, represented as a deque of positions from head to tail. */
    private final Deque<Position> body;

    /**
     * Constructs a new snake with a single segment at the specified starting position.
     *
     * @param start the initial position of the snake's head
     * @throws NullPointerException if start is null
     */
    public Snake(Position start) {
        if (start == null) {
            throw new NullPointerException("Start position cannot be null");
        }
        this.body = new ArrayDeque<>();
        this.body.offerLast(start);
    }

    /**
     * Returns the current head position of the snake.
     *
     * @return the head position
     * @throws IllegalStateException if the snake has no body segments
     */
    public Position head() {
        if (body.isEmpty()) {
            throw new IllegalStateException("Cannot get head of empty snake");
        }
        return body.peekFirst();
    }

    /**
     * Returns the current tail position of the snake.
     *
     * @return the tail position
     * @throws IllegalStateException if the snake has no body segments
     */
    public Position tail() {
        if (body.isEmpty()) {
            throw new IllegalStateException("Cannot get tail of empty snake");
        }
        return body.peekLast();
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
     * Checks if the snake occupies the specified position.
     *
     * @param p the position to check
     * @return true if any segment of the snake occupies the position, false otherwise
     * @throws NullPointerException if p is null
     */
    public boolean occupies(Position p) {
        if (p == null) {
            throw new NullPointerException("Position cannot be null");
        }
        return body.contains(p);
    }

    /**
     * Moves the snake by adding a new head position and removing the tail.
     * This simulates the snake moving one cell in its current direction.
     *
     * @param nextHead the new head position
     * @throws NullPointerException if nextHead is null
     */
    public void moveTo(Position nextHead) {
        if (nextHead == null) {
            throw new NullPointerException("Next head position cannot be null");
        }
        body.offerFirst(nextHead);
        body.pollLast();
    }

    /**
     * Grows the snake by adding a new head position while keeping the tail.
     * This simulates the snake growing when it consumes food.
     *
     * @param nextHead the new head position
     * @throws NullPointerException if nextHead is null
     */
    public void growTo(Position nextHead) {
        if (nextHead == null) {
            throw new NullPointerException("Next head position cannot be null");
        }
        body.offerFirst(nextHead);
    }

    /**
     * Returns a defensive copy of the snake's body as a list, ordered from head to tail.
     *
     * @return a new list containing the snake's body positions in order
     */
    public List<Position> bodyAsList() {
        return new ArrayList<>(body);
    }
}