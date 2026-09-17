/**
 * Deterministic offline implementation of TransferAdapter and TransferSession.
 * This class simulates a transfer process with fixed total bytes and chunk size,
 * making it suitable for testing and demos without network or filesystem access.
 */
public class OfflineDeterministicAdapter implements TransferAdapter {
    
    /**
     * The total number of bytes to transfer in each simulated download.
     */
    private static final long TOTAL_BYTES = 1000L;
    
    /**
     * The number of bytes transferred in each step.
     */
    private static final long CHUNK_SIZE = 100L;
    
    /**
     * Begins a new transfer session for the specified parameters.
     * 
     * @param url the URL to download from (not used in this deterministic implementation)
     * @param format the download format to use (not used in this deterministic implementation)
     * @param outputName the name of the output file (not used in this deterministic implementation)
     * @param listener the progress listener to notify during transfer
     * @return a TransferSession representing the ongoing transfer
     */
    @Override
    public TransferSession begin(String url, DownloadFormat format, String outputName, ProgressListener listener) {
        return new OfflineTransferSession(listener);
    }
    
    /**
     * Internal implementation of TransferSession for offline simulation.
     */
    private static class OfflineTransferSession implements TransferSession {
        
        /**
         * The progress listener to notify during transfer.
         */
        private final ProgressListener listener;
        
        /**
         * The number of bytes downloaded so far.
         */
        private long downloadedBytes;
        
        /**
         * Whether the transfer has been cancelled.
         */
        private boolean cancelled;
        
        /**
         * Constructs a new offline transfer session with the given listener.
         * 
         * @param listener the progress listener to notify during transfer
         */
        public OfflineTransferSession(ProgressListener listener) {
            this.listener = listener;
            this.downloadedBytes = 0L;
            this.cancelled = false;
        }
        
        /**
         * Performs one step of the transfer operation.
         * Advances the transfer by one deterministic chunk and returns whether more steps are needed.
         * 
         * @return true if the transfer has more steps to complete, false if finished
         */
        @Override
        public boolean step() {
            if (cancelled) {
                return false;
            }
            
            // If we've reached the total bytes, finish
            if (downloadedBytes >= TOTAL_BYTES) {
                listener.onCompleted();
                return false;
            }
            
            // Advance by one chunk
            downloadedBytes += CHUNK_SIZE;
            
            // Ensure we don't exceed total bytes
            if (downloadedBytes > TOTAL_BYTES) {
                downloadedBytes = TOTAL_BYTES;
            }
            
            // Notify progress
            listener.onProgress(downloadedBytes, TOTAL_BYTES);
            
            // Return true if more steps are needed
            return downloadedBytes < TOTAL_BYTES;
        }
        
        /**
         * Cancels the ongoing transfer operation.
         * After calling this method, the session should not perform any further work.
         */
        @Override
        public void cancel() {
            cancelled = true;
            // In a real implementation, we might want to notify the listener here
            // but since we're just simulating, we can ignore it
        }
        
        /**
         * Gets the total number of bytes expected to be transferred.
         * 
         * @return the total byte count
         */
        @Override
        public long getTotalBytes() {
            return TOTAL_BYTES;
        }
        
        /**
         * Gets the number of bytes that have been successfully transferred so far.
         * 
         * @return the downloaded byte count
         */
        @Override
        public long getDownloadedBytes() {
            return downloadedBytes;
        }
    }
}