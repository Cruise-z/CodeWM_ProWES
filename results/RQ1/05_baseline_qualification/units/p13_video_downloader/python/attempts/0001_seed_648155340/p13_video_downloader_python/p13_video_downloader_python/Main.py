"""Runtime entry point for video downloader demonstration."""

from video_downloader import DownloadRequest, DownloadQueue, FakeTransferAdapter


def run_demo() -> dict:
    """
    Run a demonstration of the video downloader with a fake transfer adapter.

    Returns:
        A dictionary containing the status of the download job.
    """
    # Define the transfer mapping
    mapping = {"https://example.com/clip": (12, 4)}
    
    # Create a fake transfer adapter
    adapter = FakeTransferAdapter(mapping)
    
    # Create a download queue
    queue = DownloadQueue(adapter)
    
    # Create a download request
    request = DownloadRequest(url="https://example.com/clip", fmt="mp4")
    
    # Enqueue the request
    job_id = queue.enqueue(request)
    
    # Process all jobs
    queue.process_all()
    
    # Get the status of the job
    return queue.get_status(job_id)


if __name__ == "__main__":
    result = run_demo()
    print(result)