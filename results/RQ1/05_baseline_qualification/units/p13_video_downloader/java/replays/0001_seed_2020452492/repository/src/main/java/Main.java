/**
 * Runtime entry point for the video downloader demo.
 * This class demonstrates the usage of the VideoDownloader API
 * with the OfflineDeterministicAdapter for a headless, offline simulation.
 */
public class Main {
    public static void main(String[] args) {
        // Create the transfer adapter for offline simulation
        OfflineDeterministicAdapter adapter = new OfflineDeterministicAdapter();
        
        // Create the video downloader with the adapter
        VideoDownloader downloader = new VideoDownloader(adapter);
        
        // Request two downloads with different formats and names
        int taskId1 = downloader.requestDownload(
            "https://example.com/video1.mp4", 
            DownloadFormat.MP4, 
            "My Video File"
        );
        
        int taskId2 = downloader.requestDownload(
            "https://example.com/video2.webm", 
            DownloadFormat.WEBM, 
            "Another Video File.txt"
        );
        
        // Start all pending downloads
        downloader.startPending();
        
        // Simulate a few ticks to show progress
        for (int i = 0; i < 5; i++) {
            downloader.tick();
            
            // Print status and progress for each task
            System.out.println("Task " + taskId1 + " Status: " + downloader.getStatus(taskId1) +
                ", Progress: " + downloader.getProgress(taskId1) + "%");
            System.out.println("Task " + taskId2 + " Status: " + downloader.getStatus(taskId2) +
                ", Progress: " + downloader.getProgress(taskId2) + "%");
            System.out.println("---");
        }
        
        // Cancel the first task
        downloader.cancel(taskId1);
        
        // Tick again to see the effect of cancellation
        downloader.tick();
        
        // Print final status
        System.out.println("Task " + taskId1 + " Status after cancellation: " + 
            downloader.getStatus(taskId1));
        System.out.println("Task " + taskId2 + " Final Status: " + 
            downloader.getStatus(taskId2));
        System.out.println("Task " + taskId1 + " Output Name: " + 
            downloader.getOutputName(taskId1));
        System.out.println("Task " + taskId2 + " Output Name: " + 
            downloader.getOutputName(taskId2));
    }
}