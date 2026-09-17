/**
 * Represents metadata for a media item.
 */
public final class MediaItem {
    private final String id;
    private final String title;
    private final long durationMillis;

    /**
     * Constructs a new MediaItem with the specified id, title, and duration.
     *
     * @param id the unique identifier for the media item (must not be blank)
     * @param title the title of the media item (must not be blank)
     * @param durationMillis the duration of the media item in milliseconds (must be positive)
     * @throws IllegalArgumentException if id or title is blank, or durationMillis is not positive
     */
    public MediaItem(String id, String title, long durationMillis) {
        if (id == null || id.trim().isEmpty()) {
            throw new IllegalArgumentException("ID must not be null or blank");
        }
        if (title == null || title.trim().isEmpty()) {
            throw new IllegalArgumentException("Title must not be null or blank");
        }
        if (durationMillis <= 0) {
            throw new IllegalArgumentException("Duration must be positive");
        }
        this.id = id;
        this.title = title;
        this.durationMillis = durationMillis;
    }

    /**
     * Gets the unique identifier for this media item.
     *
     * @return the ID
     */
    public String getId() {
        return id;
    }

    /**
     * Gets the title of this media item.
     *
     * @return the title
     */
    public String getTitle() {
        return title;
    }

    /**
     * Gets the duration of this media item in milliseconds.
     *
     * @return the duration in milliseconds
     */
    public long getDurationMillis() {
        return durationMillis;
    }
}