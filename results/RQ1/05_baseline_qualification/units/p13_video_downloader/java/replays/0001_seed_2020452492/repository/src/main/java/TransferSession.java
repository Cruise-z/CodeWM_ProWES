/**
 * Boundary interface representing an in-progress transfer.
 * This interface defines the contract for transfer sessions,
 * allowing them to be stepped forward and cancelled.
 */
public interface TransferSession {
    
    /**
     * Performs one step of the transfer operation.
     * This method should advance the transfer by one deterministic chunk
     * and return whether more steps are needed.
     *
     * @return true if the transfer has more steps to complete, false if finished
     */
    boolean step();
    
    /**
     * Cancels the ongoing transfer operation.
     * After calling this method, the session should not perform any further work.
     */
    void cancel();
    
    /**
     * Gets the total number of bytes expected to be transferred.
     *
     * @return the total byte count
     */
    long getTotalBytes();
    
    /**
     * Gets the number of bytes that have been successfully transferred so far.
     *
     * @return the downloaded byte count
     */
    long getDownloadedBytes();
}