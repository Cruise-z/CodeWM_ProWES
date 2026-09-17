import java.util.ArrayList;

/**
 * Playlist storage and navigation.
 * Backed by ArrayList<MediaItem>.
 * add rejects null.
 * size/getAt/removeAt use standard list semantics.
 * hasNext/hasPrevious are bounds-safe.
 * nextIndex/previousIndex clamp for nonempty lists and return -1 for empty.
 */
public final class Playlist {
    private final ArrayList<MediaItem> items;

    /**
     * Constructs a new empty Playlist.
     */
    public Playlist() {
        this.items = new ArrayList<>();
    }

    /**
     * Adds a media item to the playlist.
     *
     * @param item the media item to add (must not be null)
     * @throws IllegalArgumentException if item is null
     */
    public void add(MediaItem item) {
        if (item == null) {
            throw new IllegalArgumentException("Item must not be null");
        }
        items.add(item);
    }

    /**
     * Returns the number of items in the playlist.
     *
     * @return the size of the playlist
     */
    public int size() {
        return items.size();
    }

    /**
     * Gets the media item at the specified index.
     *
     * @param index the index of the item to retrieve
     * @return the media item at the specified index
     * @throws IndexOutOfBoundsException if the index is out of range
     */
    public MediaItem getAt(int index) {
        return items.get(index);
    }

    /**
     * Removes the media item at the specified index.
     *
     * @param index the index of the item to remove
     * @return the removed media item
     * @throws IndexOutOfBoundsException if the index is out of range
     */
    public MediaItem removeAt(int index) {
        return items.remove(index);
    }

    /**
     * Checks if there is a next item after the given index.
     *
     * @param index the current index
     * @return true if there is a next item, false otherwise
     */
    public boolean hasNext(int index) {
        return index >= 0 && index < items.size() - 1;
    }

    /**
     * Checks if there is a previous item before the given index.
     *
     * @param index the current index
     * @return true if there is a previous item, false otherwise
     */
    public boolean hasPrevious(int index) {
        return index > 0 && index < items.size();
    }

    /**
     * Gets the next index, clamped to valid range.
     *
     * @param index the current index
     * @return the next valid index, or -1 if playlist is empty
     */
    public int nextIndex(int index) {
        if (items.isEmpty()) {
            return -1;
        }
        int next = index + 1;
        return Math.min(next, items.size() - 1);
    }

    /**
     * Gets the previous index, clamped to valid range.
     *
     * @param index the current index
     * @return the previous valid index, or -1 if playlist is empty
     */
    public int previousIndex(int index) {
        if (items.isEmpty()) {
            return -1;
        }
        int prev = index - 1;
        return Math.max(prev, 0);
    }
}