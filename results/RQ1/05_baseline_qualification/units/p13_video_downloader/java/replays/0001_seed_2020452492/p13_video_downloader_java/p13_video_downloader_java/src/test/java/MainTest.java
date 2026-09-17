import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

public class MainTest {

    @Test
    public void testRuntimeWiring() {
        // Test that we can wire up the components correctly
        OfflineDeterministicAdapter adapter = new OfflineDeterministicAdapter();
        VideoDownloader downloader = new VideoDownloader(adapter);
        
        assertNotNull(adapter);
        assertNotNull(downloader);
    }

    @Test
    public void testValidationAndNaming() {
        // Test URL validation and naming rules
        OfflineDeterministicAdapter adapter = new OfflineDeterministicAdapter();
        VideoDownloader downloader = new VideoDownloader(adapter);
        
        // Valid URL should work
        int taskId = downloader.requestDownload(
            "https://example.com/video.mp4", 
            DownloadFormat.MP4, 
            "Valid File Name"
        );
        
        assertEquals("Valid File Name.mp4", downloader.getOutputName(taskId));
        
        // Invalid URL should throw exception
        assertThrows(IllegalArgumentException.class, () -> {
            downloader.requestDownload(
                "not-a-url", 
                DownloadFormat.MP4, 
                "Any Name"
            );
        });
        
        // Test name sanitization with dangerous characters
        int taskId2 = downloader.requestDownload(
            "https://example.com/video.webm", 
            DownloadFormat.WEBM, 
            "File <with> \"quotes\" and |pipes|"
        );
        
        // Should be sanitized and have correct extension
        assertEquals("File _with_ _quotes_ and _pipes_.webm", downloader.getOutputName(taskId2));
    }

    @Test
    public void testProgressAndCompletion() {
        // Test that progress reaches 100% deterministically
        OfflineDeterministicAdapter adapter = new OfflineDeterministicAdapter();
        VideoDownloader downloader = new VideoDownloader(adapter);
        
        int taskId = downloader.requestDownload(
            "https://example.com/video.mp4", 
            DownloadFormat.MP4, 
            "Test File"
        );
        
        // Start the download
        downloader.startPending();
        
        // Tick until completion
        while (downloader.getStatus(taskId) != DownloadStatus.COMPLETED) {
            downloader.tick();
        }
        
        // Verify completion
        assertEquals(DownloadStatus.COMPLETED, downloader.getStatus(taskId));
        assertEquals(100, downloader.getProgress(taskId));
    }

    @Test
    public void testCancellation() {
        // Test cancellation behavior
        OfflineDeterministicAdapter adapter = new OfflineDeterministicAdapter();
        VideoDownloader downloader = new VideoDownloader(adapter);
        
        int taskId = downloader.requestDownload(
            "https://example.com/video.mp4", 
            DownloadFormat.MP4, 
            "Cancellable File"
        );
        
        // Start the download
        downloader.startPending();
        
        // Tick once to make it running
        downloader.tick();
        
        // Verify it's running
        assertEquals(DownloadStatus.RUNNING, downloader.getStatus(taskId));
        
        // Cancel it
        downloader.cancel(taskId);
        
        // Verify it's cancelled
        assertEquals(DownloadStatus.CANCELLED, downloader.getStatus(taskId));
        
        // Tick again - should not change status
        downloader.tick();
        assertEquals(DownloadStatus.CANCELLED, downloader.getStatus(taskId));
    }
}