/**
 * Immutable snapshot of the player state at a particular moment.
 * Provides a consistent view of the playlist, player state, and volume control.
 */
public final class PlayerSnapshot {
    private final int index;
    private final String title;
    private final long positionMillis;
    private final long durationMillis;
    private final PlayerState.PlaybackStatus status;
    private final int volume;
    private final boolean muted;

    /**
     * Constructs a new PlayerSnapshot with the specified values.
     *
     * @param index the current index in the playlist
     * @param title the title of the current media item
     * @param positionMillis the current playback position in milliseconds
     * @param durationMillis the duration of the current media item in milliseconds
     * @param status the current playback status
     * @param volume the current volume level
     * @param muted whether the player is currently muted
     */
    public PlayerSnapshot(
            int index,
            String title,
            long positionMillis,
            long durationMillis,
            PlayerState.PlaybackStatus status,
            int volume,
            boolean muted) {
        this.index = index;
        this.title = title;
        this.positionMillis = positionMillis;
        this.durationMillis = durationMillis;
        this.status = status;
        this.volume = volume;
        this.muted = muted;
    }

    /**
     * Gets the current index in the playlist.
     *
     * @return the current index
     */
    public int getIndex() {
        return index;
    }

    /**
     * Gets the title of the current media item.
     *
     * @return the title
     */
    public String getTitle() {
        return title;
    }

    /**
     * Gets the current playback position in milliseconds.
     *
     * @return the current position in milliseconds
     */
    public long getPositionMillis() {
        return positionMillis;
    }

    /**
     * Gets the duration of the current media item in milliseconds.
     *
     * @return the duration in milliseconds
     */
    public long getDurationMillis() {
        return durationMillis;
    }

    /**
     * Gets the current playback status.
     *
     * @return the current playback status
     */
    public PlayerState.PlaybackStatus getStatus() {
        return status;
    }

    /**
     * Gets the current volume level.
     *
     * @return the current volume (0-100)
     */
    public int getVolume() {
        return volume;
    }

    /**
     * Checks if the player is currently muted.
     *
     * @return true if muted, false otherwise
     */
    public boolean isMuted() {
        return muted;
    }

    /**
     * Creates a PlayerSnapshot from the current state of the playlist, player state, and volume control.
     *
     * @param playlist the playlist
     * @param state the player state
     * @param volumeControl the volume control
     * @return a new PlayerSnapshot with the current state
     */
    public static PlayerSnapshot from(Playlist playlist, PlayerState state, VolumeControl volumeControl) {
        int currentIndex = state.getCurrentIndex();
        String title = "";
        long durationMillis = 0;
        
        // Handle case where playlist is empty or index is invalid
        if (playlist != null && currentIndex >= 0 && currentIndex < playlist.size()) {
            MediaItem currentItem = playlist.getAt(currentIndex);
            if (currentItem != null) {
                title = currentItem.getTitle();
                durationMillis = currentItem.getDurationMillis();
            }
        }
        
        return new PlayerSnapshot(
                currentIndex,
                title,
                state.getPositionMillis(),
                durationMillis,
                state.getStatus(),
                volumeControl.getVolume(),
                volumeControl.isMuted()
        );
    }
}