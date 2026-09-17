/**
 * Volume control for the media player.
 * Manages volume level, mute state, and effective volume calculation.
 */
public final class VolumeControl {
    private int volume;
    private int lastNonMuted;
    private boolean muted;

    /**
     * Constructs a new VolumeControl with default settings.
     * Initializes volume=100, lastNonMuted=100, muted=false.
     */
    public VolumeControl() {
        this.volume = 100;
        this.lastNonMuted = 100;
        this.muted = false;
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
     * Sets the volume level.
     * Validates that the volume is within the range [0, 100].
     * Always updates both volume and lastNonMuted, even when muted.
     *
     * @param volume the new volume level (must be between 0 and 100 inclusive)
     * @throws IllegalArgumentException if volume is outside the valid range
     */
    public void setVolume(int volume) {
        if (volume < 0 || volume > 100) {
            throw new IllegalArgumentException("Volume must be between 0 and 100 inclusive");
        }
        this.volume = volume;
        this.lastNonMuted = volume;
    }

    /**
     * Gets the last non-muted volume level.
     *
     * @return the last non-muted volume level
     */
    public int getLastNonMuted() {
        return lastNonMuted;
    }

    /**
     * Checks if the volume is currently muted.
     *
     * @return true if muted, false otherwise
     */
    public boolean isMuted() {
        return muted;
    }

    /**
     * Mutes the volume.
     * Sets muted=true without changing the volume levels.
     */
    public void mute() {
        this.muted = true;
    }

    /**
     * Unmutes the volume.
     * Sets muted=false and restores the volume to the last non-muted level.
     */
    public void unmute() {
        this.muted = false;
        this.volume = this.lastNonMuted;
    }

    /**
     * Gets the effective volume.
     * Returns 0 if muted, otherwise returns the current volume.
     *
     * @return the effective volume (0 if muted, otherwise current volume)
     */
    public int getEffectiveVolume() {
        return muted ? 0 : volume;
    }
}