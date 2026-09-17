/**
 * Progress listener interface for receiving transfer progress updates.
 * This interface defines the contract for progress callbacks during a transfer operation.
 */
public interface ProgressListener {
    
    /**
     * Called periodically to report transfer progress.
     *
     * @param downloaded the number of bytes downloaded so far
     * @param total the total number of bytes to download
     */
    void onProgress(long downloaded, long total);
    
    /**
     * Called when the transfer completes successfully.
     */
    void onCompleted();
    
    /**
     * Called when the transfer fails.
     *
     * @param message a descriptive message about the failure
     */
    void onFailed(String message);
}