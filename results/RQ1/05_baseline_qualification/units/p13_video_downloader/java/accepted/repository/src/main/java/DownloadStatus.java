/**
 * Enumeration of download lifecycle statuses.
 * Represents the possible states of a download task.
 */
public enum DownloadStatus {
    /**
     * The download has been created but not yet started.
     */
    PENDING,

    /**
     * The download is currently in progress.
     */
    RUNNING,

    /**
     * The download has completed successfully.
     */
    COMPLETED,

    /**
     * The download has failed due to an error.
     */
    FAILED,

    /**
     * The download has been cancelled by the user.
     */
    CANCELLED
}