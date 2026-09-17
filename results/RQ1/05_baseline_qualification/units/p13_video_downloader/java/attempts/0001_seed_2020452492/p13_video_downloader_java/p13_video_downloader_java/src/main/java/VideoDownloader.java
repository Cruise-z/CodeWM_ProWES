/**
 * Orchestrator class managing a queue of download tasks.
 * Provides the canonical public API for requesting, starting, ticking,
 * cancelling, and querying download tasks.
 */
import java.util.HashMap;
import java.util.Map;

public class VideoDownloader {
    private final TransferAdapter adapter;
    private final Map<Integer, DownloadTask> tasks;
    private int nextId;

    /**
     * Constructs a new VideoDownloader with the specified transfer adapter.
     *
     * @param adapter the transfer adapter to use for starting downloads
     */
    public VideoDownloader(TransferAdapter adapter) {
        this.adapter = adapter;
        this.tasks = new HashMap<>();
        this.nextId = 0;
    }

    /**
     * Requests a new download with the given parameters.
     * Creates a VideoDownloadRequest and stores a new PENDING task.
     *
     * @param url the URL to download from
     * @param format the download format to use
     * @param suggestedName the suggested name for the output file
     * @return the unique ID assigned to the new task
     * @throws IllegalArgumentException if the URL is invalid or any parameter is null
     */
    public int requestDownload(String url, DownloadFormat format, String suggestedName) {
        VideoDownloadRequest request = VideoDownloadRequest.of(url, format, suggestedName);
        int id = nextId++;
        DownloadTask task = new DownloadTask(id, request);
        tasks.put(id, task);
        return id;
    }

    /**
     * Starts all PENDING download tasks.
     * Transitions them to RUNNING state and begins their transfers.
     */
    public void startPending() {
        for (DownloadTask task : tasks.values()) {
            if (task.getStatus() == DownloadStatus.PENDING) {
                task.start(adapter);
            }
        }
    }

    /**
     * Advances all RUNNING download tasks by one step.
     * Updates their progress and status accordingly.
     */
    public void tick() {
        for (DownloadTask task : tasks.values()) {
            if (task.getStatus() == DownloadStatus.RUNNING) {
                task.tick();
            }
        }
    }

    /**
     * Cancels the download task with the specified ID.
     * If the task is PENDING or RUNNING, it will be cancelled.
     * If the task is already COMPLETED, FAILED, or CANCELLED, this operation has no effect.
     *
     * @param taskId the ID of the task to cancel
     * @throws IllegalArgumentException if the task ID is unknown
     */
    public void cancel(int taskId) {
        DownloadTask task = tasks.get(taskId);
        if (task == null) {
            throw new IllegalArgumentException("Unknown task ID: " + taskId);
        }
        task.cancel();
    }

    /**
     * Gets the current status of the download task with the specified ID.
     *
     * @param taskId the ID of the task to query
     * @return the current status of the task
     * @throws IllegalArgumentException if the task ID is unknown
     */
    public DownloadStatus getStatus(int taskId) {
        DownloadTask task = tasks.get(taskId);
        if (task == null) {
            throw new IllegalArgumentException("Unknown task ID: " + taskId);
        }
        return task.getStatus();
    }

    /**
     * Gets the current progress percentage of the download task with the specified ID.
     *
     * @param taskId the ID of the task to query
     * @return the progress as an integer between 0 and 100
     * @throws IllegalArgumentException if the task ID is unknown
     */
    public int getProgress(int taskId) {
        DownloadTask task = tasks.get(taskId);
        if (task == null) {
            throw new IllegalArgumentException("Unknown task ID: " + taskId);
        }
        return task.getProgress();
    }

    /**
     * Gets the computed output name of the download task with the specified ID.
     *
     * @param taskId the ID of the task to query
     * @return the output filename
     * @throws IllegalArgumentException if the task ID is unknown
     */
    public String getOutputName(int taskId) {
        DownloadTask task = tasks.get(taskId);
        if (task == null) {
            throw new IllegalArgumentException("Unknown task ID: " + taskId);
        }
        return task.getOutputName();
    }
}