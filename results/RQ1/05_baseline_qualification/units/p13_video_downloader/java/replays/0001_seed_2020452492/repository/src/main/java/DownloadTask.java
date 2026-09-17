/**
 * Domain entity representing a single download task in the queue.
 * Manages the state machine for a download including progress tracking,
 * start, tick, and cancellation operations.
 */
public class DownloadTask {
    private final int id;
    private final VideoDownloadRequest request;
    private DownloadStatus status;
    private TransferSession session;
    private int progress;

    /**
     * Constructs a new download task with the given ID and request.
     *
     * @param id the unique identifier for this task
     * @param request the download request containing URL, format, and naming info
     */
    public DownloadTask(int id, VideoDownloadRequest request) {
        this.id = id;
        this.request = request;
        this.status = DownloadStatus.PENDING;
        this.progress = 0;
        this.session = null;
    }

    /**
     * Gets the unique identifier for this download task.
     *
     * @return the task ID
     */
    public int getId() {
        return id;
    }

    /**
     * Gets the current status of this download task.
     *
     * @return the download status
     */
    public DownloadStatus getStatus() {
        return status;
    }

    /**
     * Gets the progress percentage of this download task.
     *
     * @return the progress as an integer between 0 and 100
     */
    public int getProgress() {
        return progress;
    }

    /**
     * Gets the computed output name for this download task.
     *
     * @return the output filename
     */
    public String getOutputName() {
        return request.getOutputName();
    }

    /**
     * Starts this download task using the provided transfer adapter.
     * Transitions the task from PENDING to RUNNING state.
     *
     * @param adapter the transfer adapter to use for starting the download
     * @throws IllegalStateException if the task is not in PENDING state
     */
    public void start(TransferAdapter adapter) {
        if (status != DownloadStatus.PENDING) {
            throw new IllegalStateException("Task must be in PENDING state to start");
        }
        
        // Create a progress listener that updates task state
        ProgressListener listener = new ProgressListener() {
            @Override
            public void onProgress(long downloaded, long total) {
                // Update progress percentage
                if (total > 0) {
                    progress = (int) ((downloaded * 100) / total);
                } else {
                    progress = 0;
                }
            }

            @Override
            public void onCompleted() {
                status = DownloadStatus.COMPLETED;
            }

            @Override
            public void onFailed(String message) {
                status = DownloadStatus.FAILED;
            }
        };
        
        // Begin the transfer session
        session = adapter.begin(
            request.getUrl(),
            request.getFormat(),
            request.getOutputName(),
            listener
        );
        
        status = DownloadStatus.RUNNING;
    }

    /**
     * Advances this download task by one step if it is currently running.
     * Updates the progress and status based on the underlying transfer session.
     *
     * @throws IllegalStateException if the task is not in RUNNING state
     */
    public void tick() {
        if (status != DownloadStatus.RUNNING) {
            throw new IllegalStateException("Task must be in RUNNING state to tick");
        }
        
        if (session != null) {
            boolean hasMore = session.step();
            
            if (!hasMore) {
                // If no more steps, mark as completed
                status = DownloadStatus.COMPLETED;
            }
        }
    }

    /**
     * Cancels this download task if it is currently running or pending.
     * Transition the task to CANCELLED state and cancels the underlying session.
     */
    public void cancel() {
        if (status == DownloadStatus.CANCELLED) {
            // Already cancelled, do nothing
            return;
        }
        
        if (session != null) {
            session.cancel();
        }
        
        status = DownloadStatus.CANCELLED;
    }
}