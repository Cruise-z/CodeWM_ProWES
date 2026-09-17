import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;

/**
 * Represents the snake in the game, maintaining its body as an ordered sequence of positions.
 */
public final class Snake {
    /** The body of the snake, stored as a deque with head at the front. */
    private final Deque<Position> body;

    /**
     * Constructs a new snake with a single segment at the specified position.
     *
     * @param start the initial position of the snake's head
     * @throws NullPointerException if start is null
     */
    public Snake(Position start) {
        if (start == null) {
            throw new NullPointerException("Start position cannot be null");
        }
        this.body = new ArrayDeque<>();
        this.body.addLast(start);
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
        return body.getFirst();
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
        return body.getLast();
    }

    /**
     * Returns the length of the snake (number of segments).
     *
     * @return the length of the snake
     */
    public int length() {
        return body.size();
    }

    /**
     * Checks if the snake occupies the specified position.
     *
     * @param p the position to check
     * @return true if any segment of the snake occupies this position
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
     * This method is used for normal movement where the snake doesn't grow.
     *
     * @param nextHead the new head position
     * @throws NullPointerException if nextHead is null
     */
    public void moveTo(Position nextHead) {
        if (nextHead == null) {
            throw new NullPointerException("Next head position cannot be null");
        }
        body.addFirst(nextHead);
        body.removeLast();
    }

    /**
     * Grows the snake by adding a new head position while keeping the tail.
     * This method is used when the snake eats food.
     *
     * @param nextHead the new head position
     * @throws NullPointerException if nextHead is null
     */
    public void growTo(Position nextHead) {
        if (nextHead == null) {
            throw new NullPointerException("Next head position cannot be null");
        }
        body.addFirst(nextHead);
    }

    /**
     * Returns a defensive copy of the snake's body as a list.
     * The returned list represents the body from head to tail.
     *
     * @return a new list containing the snake's body positions
     */
    public List<Position> bodyAsList() {
        return new ArrayList<>(body);
    }
}