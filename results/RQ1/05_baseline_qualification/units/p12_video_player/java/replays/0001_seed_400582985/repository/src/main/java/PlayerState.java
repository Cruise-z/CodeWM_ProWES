/**
 * Player state container.
 * Holds playback status and cursor information.
 */
public final class PlayerState {
    /**
     * Enum representing the playback status.
     */
    public enum PlaybackStatus {
        STOPPED,
        PLAYING,
        PAUSED
    }

    private int currentIndex;
    private long positionMillis;
    private PlaybackStatus status;

    /**
     * Constructs a new PlayerState with default values.
     * Initializes currentIndex=0, positionMillis=0, and status=STOPPED.
     */
    public PlayerState() {
        this.currentIndex = 0;
        this.positionMillis = 0;
        this.status = PlaybackStatus.STOPPED;
    }

    /**
     * Gets the current index in the playlist.
     *
     * @return the current index
     */
    public int getCurrentIndex() {
        return currentIndex;
    }

    /**
     * Sets the current index in the playlist.
     *
     * @param index the new index
     */
    public void setCurrentIndex(int index) {
        this.currentIndex = index;
    }

    /**
     * Gets the current position in milliseconds.
     *
     * @return the current position in milliseconds
     */
    public long getPositionMillis() {
        return positionMillis;
    }

    /**
     * Sets the current position in milliseconds.
     * Throws IllegalArgumentException if position is negative.
     *
     * @param positionMillis the new position in milliseconds
     * @throws IllegalArgumentException if position is negative
     */
    public void setPositionMillis(long positionMillis) {
        if (positionMillis < 0) {
            throw new IllegalArgumentException("Position must not be negative");
        }
        this.positionMillis = positionMillis;
    }

    /**
     * Gets the current playback status.
     *
     * @return the current playback status
     */
    public PlaybackStatus getStatus() {
        return status;
    }

    /**
     * Sets the current playback status.
     * Throws NullPointerException if status is null.
     *
     * @param status the new playback status
     * @throws NullPointerException if status is null
     */
    public void setStatus(PlaybackStatus status) {
        if (status == null) {
            throw new NullPointerException("Status must not be null");
        }
        this.status = status;
    }

    /**
     * Resets the position to 0.
     */
    public void resetPosition() {
        this.positionMillis = 0;
    }
}