/**
 * Main entry point for the video player demonstration.
 * Constructs a small in-memory playlist and deterministic clock,
 * runs a bounded demo, and exits without input or loops.
 */
public class Main {
    /**
     * Main method - entry point of the application.
     * Demonstrates basic playback functionality with a simple playlist.
     *
     * @param args command-line arguments (not used)
     */
    public static void main(String[] args) {
        // Create a simple playlist with two media items
        Playlist playlist = new Playlist();
        playlist.add(new MediaItem("1", "Video 1", 3000));
        playlist.add(new MediaItem("2", "Video 2", 4000));

        // Create volume control and deterministic clock
        VolumeControl volumeControl = new VolumeControl();
        DeterministicClock clock = new DeterministicClock();

        // Create playback controller
        PlaybackController controller = new PlaybackController(playlist, volumeControl, clock);

        // Demonstrate playback sequence
        controller.play();
        clock.advance(1000);
        controller.onClockAdvanced();

        // Print snapshot information
        PlayerSnapshot snapshot = controller.getSnapshot();
        System.out.println("Index: " + snapshot.getIndex() +
                          ", Title: " + snapshot.getTitle() +
                          ", Position: " + snapshot.getPositionMillis() +
                          ", Duration: " + snapshot.getDurationMillis() +
                          ", Status: " + snapshot.getStatus() +
                          ", Volume: " + snapshot.getVolume() +
                          ", Muted: " + snapshot.isMuted());

        // Exit successfully
    }
}