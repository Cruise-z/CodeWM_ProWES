"""Runtime entrypoint for the video downloader demo."""

from video_downloader import (
    DownloadRequest,
    DownloadQueue,
    FakeTransferAdapter,
    run_demo
)


def run_demo() -> dict:
    """Run a demonstration of the video downloader.

    Returns:
        A status dictionary for the completed download.
    """
    # Create a fake transfer adapter with the specified mapping
    mapping = {"https://example.com/clip": (12, 4)}
    adapter = FakeTransferAdapter(mapping)
    
    # Create a download queue with the adapter
    queue = DownloadQueue(adapter)
    
    # Create a download request for an MP4 file
    request = DownloadRequest(
        url="https://example.com/clip",
        fmt="mp4"
    )
    
    # Enqueue the request
    job_id = queue.enqueue(request)
    
    # Process all jobs
    queue.process_all()
    
    # Return the status of the job
    return queue.get_status(job_id)


if __name__ == "__main__":
    # Run the demo and print the result
    result = run_demo()
    print(result)