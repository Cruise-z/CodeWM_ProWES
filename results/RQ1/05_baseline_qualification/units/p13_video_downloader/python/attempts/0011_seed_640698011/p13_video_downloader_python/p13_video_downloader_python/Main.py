"""Runtime entry point for the video downloader demonstration."""

from video_downloader import DownloadRequest, DownloadQueue, FakeTransferAdapter


def run_demo() -> dict:
    """
    Run a demonstration of the video downloader with a fake transfer adapter.

    Returns:
        A dictionary containing the status of the download job.
    """
    # Create a fake transfer adapter with a mapping for the demo URL
    mapping = {"https://example.com/clip": (12, 4)}
    adapter = FakeTransferAdapter(mapping)

    # Create a download queue with the fake adapter
    queue = DownloadQueue(adapter)

    # Create a download request for an MP4 file
    request = DownloadRequest("https://example.com/clip", "mp4")

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