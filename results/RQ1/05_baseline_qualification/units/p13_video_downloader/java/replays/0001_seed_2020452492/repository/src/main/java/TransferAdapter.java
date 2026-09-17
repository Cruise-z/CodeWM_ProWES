/**
 * Boundary interface for starting transfer sessions.
 * This interface defines the contract for beginning transfer operations,
 * decoupling the domain logic from environment-specific implementations.
 */
public interface TransferAdapter {
    
    /**
     * Begins a new transfer session for the specified parameters.
     *
     * @param url the URL to download from
     * @param format the download format to use
     * @param outputName the name of the output file
     * @param listener the progress listener to notify during transfer
     * @return a TransferSession representing the ongoing transfer
     */
    TransferSession begin(String url, DownloadFormat format, String outputName, ProgressListener listener);
}