import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class MainTest {

    @Test
    public void testSingleItemEndOfMediaStopped() {
        // Test 1: single item 5000ms
        Playlist playlist = new Playlist();
        playlist.add(new MediaItem("1", "Video 1", 5000));
        
        VolumeControl volumeControl = new VolumeControl();
        DeterministicClock clock = new DeterministicClock();
        
        PlaybackController controller = new PlaybackController(playlist, volumeControl, clock);
        
        controller.play();
        clock.advance(5000);
        controller.onClockAdvanced();
        
        PlayerSnapshot snapshot = controller.getSnapshot();
        
        assertEquals(0, snapshot.getIndex());
        assertEquals(5000, snapshot.getPositionMillis());
        assertEquals(5000, snapshot.getDurationMillis());
        assertEquals(PlayerState.PlaybackStatus.STOPPED, snapshot.getStatus());
    }

    @Test
    public void testTwoItemsNavigationAndClamping() {
        // Test 2: two items 3000/4000
        Playlist playlist = new Playlist();
        playlist.add(new MediaItem("1", "Video 1", 3000));
        playlist.add(new MediaItem("2", "Video 2", 4000));
        
        VolumeControl volumeControl = new VolumeControl();
        DeterministicClock clock = new DeterministicClock();
        
        PlaybackController controller = new PlaybackController(playlist, volumeControl, clock);
        
        // Initial play at index 0
        controller.play();
        
        // Seek 5000 should clamp to 3000 (duration of first item)
        controller.seek(5000);
        assertEquals(3000, controller.getState().getPositionMillis());
        
        // Next should go to index 1, position 0
        controller.next();
        assertEquals(1, controller.getState().getCurrentIndex());
        assertEquals(0, controller.getState().getPositionMillis());
        
        // Second next should stay at index 1
        controller.next();
        assertEquals(1, controller.getState().getCurrentIndex());
        
        // Previous should go back to index 0
        controller.previous();
        assertEquals(0, controller.getState().getCurrentIndex());
        
        // Second previous should stay at index 0
        controller.previous();
        assertEquals(0, controller.getState().getCurrentIndex());
    }

    @Test
    public void testVolumeMuteUnmuteSemantics() {
        // Test 3: volume controls
        VolumeControl volumeControl = new VolumeControl();
        
        // Set volume to 70
        volumeControl.setVolume(70);
        assertEquals(70, volumeControl.getVolume());
        assertEquals(70, volumeControl.getLastNonMuted());
        
        // Mute should make effective volume 0
        volumeControl.mute();
        assertEquals(70, volumeControl.getVolume());
        assertEquals(0, volumeControl.getEffectiveVolume());
        
        // Set volume to 30 while muted
        volumeControl.setVolume(30);
        assertEquals(30, volumeControl.getVolume());
        assertEquals(30, volumeControl.getLastNonMuted());
        assertEquals(0, volumeControl.getEffectiveVolume());
        
        // Unmute should restore volume to 30 and effective volume to 30
        volumeControl.unmute();
        assertEquals(30, volumeControl.getVolume());
        assertEquals(30, volumeControl.getEffectiveVolume());
    }
}