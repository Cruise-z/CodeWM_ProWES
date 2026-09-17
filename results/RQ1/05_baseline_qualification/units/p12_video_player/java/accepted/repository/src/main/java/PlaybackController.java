/**
 * Orchestrates playback operations for a media player.
 * Coordinates between Playlist, VolumeControl, DeterministicClock, and PlayerState.
 */
public final class PlaybackController {
    private final Playlist playlist;
    private final VolumeControl volumeControl;
    private final DeterministicClock clock;
    private PlayerState state;
    private long lastTick;

    /**
     * Constructs a new PlaybackController with the specified components.
     *
     * @param playlist the playlist to play from (must not be null)
     * @param volumeControl the volume control (must not be null)
     * @param clock the deterministic clock (must not be null)
     * @throws NullPointerException if any parameter is null
     */
    public PlaybackController(Playlist playlist, VolumeControl volumeControl, DeterministicClock clock) {
        if (playlist == null) {
            throw new NullPointerException("Playlist must not be null");
        }
        if (volumeControl == null) {
            throw new NullPointerException("VolumeControl must not be null");
        }
        if (clock == null) {
            throw new NullPointerException("Clock must not be null");
        }
        
        this.playlist = playlist;
        this.volumeControl = volumeControl;
        this.clock = clock;
        this.state = new PlayerState();
        this.lastTick = clock.getCurrentTimeMillis();
    }

    /**
     * Starts playing the current item in the playlist.
     * If the playlist is empty, throws IllegalStateException.
     * If the current position equals the duration, resets position to 0.
     * Sets the playback status to PLAYING.
     *
     * @throws IllegalStateException if the playlist is empty
     */
    public void play() {
        if (playlist.size() == 0) {
            throw new IllegalStateException("Cannot play empty playlist");
        }
        
        // Reset position only if we're at the end of the current item
        MediaItem currentItem = playlist.getAt(state.getCurrentIndex());
        if (state.getPositionMillis() >= currentItem.getDurationMillis()) {
            state.resetPosition();
        }
        
        state.setStatus(PlayerState.PlaybackStatus.PLAYING);
    }

    /**
     * Pauses the playback.
     * Sets the playback status to PAUSED.
     */
    public void pause() {
        state.setStatus(PlayerState.PlaybackStatus.PAUSED);
    }

    /**
     * Stops the playback.
     * Sets the playback status to STOPPED and resets the position to 0.
     */
    public void stop() {
        state.setStatus(PlayerState.PlaybackStatus.STOPPED);
        state.resetPosition();
    }

    /**
     * Seeks to the specified position in the current item.
     * Clamps the position to [0, current item's duration].
     *
     * @param positionMillis the desired position in milliseconds
     */
    public void seek(long positionMillis) {
        MediaItem currentItem = playlist.getAt(state.getCurrentIndex());
        long duration = currentItem.getDurationMillis();
        long clampedPosition = Math.max(0, Math.min(positionMillis, duration));
        state.setPositionMillis(clampedPosition);
    }

    /**
     * Moves to the next item in the playlist.
     * If the current index is at the end, remains at the last item.
     * Resets position to 0 if the index changes.
     */
    public void next() {
        int currentIndex = state.getCurrentIndex();
        int nextIndex = playlist.nextIndex(currentIndex);
        
        // Only change index and reset position if index actually changes
        if (nextIndex != currentIndex) {
            state.setCurrentIndex(nextIndex);
            state.resetPosition();
        }
    }

    /**
     * Moves to the previous item in the playlist.
     * If the current index is at the beginning, remains at the first item.
     * Resets position to 0 if the index changes.
     */
    public void previous() {
        int currentIndex = state.getCurrentIndex();
        int prevIndex = playlist.previousIndex(currentIndex);
        
        // Only change index and reset position if index actually changes
        if (prevIndex != currentIndex) {
            state.setCurrentIndex(prevIndex);
            state.resetPosition();
        }
    }

    /**
     * Handles clock advancement events.
     * Updates the player state based on elapsed time while playing.
     * When reaching the end of an item, transitions to STOPPED status.
     */
    public void onClockAdvanced() {
        long now = clock.getCurrentTimeMillis();
        long delta = Math.max(0, now - lastTick);
        lastTick = now;
        
        if (state.getStatus() == PlayerState.PlaybackStatus.PLAYING) {
            long currentPosition = state.getPositionMillis();
            MediaItem currentItem = playlist.getAt(state.getCurrentIndex());
            long duration = currentItem.getDurationMillis();
            
            long newPosition = currentPosition + delta;
            
            // Clamp position to duration
            if (newPosition >= duration) {
                state.setPositionMillis(duration);
                state.setStatus(PlayerState.PlaybackStatus.STOPPED);
            } else {
                state.setPositionMillis(newPosition);
            }
        }
    }

    /**
     * Gets an immutable snapshot of the current player state.
     *
     * @return a PlayerSnapshot representing the current state
     */
    public PlayerSnapshot getSnapshot() {
        return PlayerSnapshot.from(playlist, state, volumeControl);
    }

    /**
     * Gets the current player state.
     *
     * @return the PlayerState object
     */
    public PlayerState getState() {
        return state;
    }

    /**
     * Gets the playlist associated with this controller.
     *
     * @return the Playlist object
     */
    public Playlist getPlaylist() {
        return playlist;
    }

    /**
     * Gets the volume control associated with this controller.
     *
     * @return the VolumeControl object
     */
    public VolumeControl getVolumeControl() {
        return volumeControl;
    }
}