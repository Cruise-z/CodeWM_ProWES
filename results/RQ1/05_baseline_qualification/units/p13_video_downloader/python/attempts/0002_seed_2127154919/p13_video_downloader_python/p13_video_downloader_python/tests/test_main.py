"""Test cases for the video downloader demonstration."""

from video_downloader import (
    InvalidURLError,
    InvalidFormatError,
    validate_url,
    sanitize_filename,
    unique_name,
    DownloadRequest,
    Progress,
    CancellationToken,
    TransferAdapter,
    TransferResult,
    FakeTransferAdapter,
    DownloadQueue,
)
from Main import run_demo


def test_demo_completion():
    """Test that run_demo returns a completed status with 12/12 transferred."""
    result = run_demo()
    assert result["state"] == "completed"
    assert result["transferred"] == 12
    assert result["total"] == 12
    assert result["final_name"] == "clip.mp4"


def test_validation_errors():
    """Test URL and format validation errors."""
    # Test invalid URL schemes
    try:
        validate_url("ftp://example.com/file")
        assert False, "Should have raised InvalidURLError"
    except InvalidURLError:
        pass  # Expected
    
    try:
        validate_url("https://example.com/file with spaces")
        assert False, "Should have raised InvalidURLError"
    except InvalidURLError:
        pass  # Expected
        
    try:
        validate_url("")
        assert False, "Should have raised InvalidURLError"
    except InvalidURLError:
        pass  # Expected
    
    # Test invalid format
    try:
        DownloadRequest("https://example.com/file", "avi")
        assert False, "Should have raised InvalidFormatError"
    except InvalidFormatError:
        pass  # Expected


def test_naming_fixtures():
    """Test naming fixtures."""
    assert sanitize_filename("my clip") == "my_clip"
    assert unique_name("clip.mp4", {"clip.mp4"}) == "clip (1).mp4"


def test_queue_cancellation():
    """Test synchronous queue pre-start cancellation fixture."""
    # Create a fake transfer adapter with two mappings
    mapping = {"a": (12, 4), "b": (8, 4)}
    adapter = FakeTransferAdapter(mapping)
    
    # Create a download queue with the adapter
    queue = DownloadQueue(adapter)
    
    # Create two download requests
    request_a = DownloadRequest(url="a", fmt="mp4")
    request_b = DownloadRequest(url="b", fmt="mp4")
    
    # Enqueue both requests
    job_id_a = queue.enqueue(request_a)
    job_id_b = queue.enqueue(request_b)
    
    # Cancel the first job while it's pending
    assert queue.cancel(job_id_a) == True
    
    # Process all jobs
    queue.process_all()
    
    # Check results
    status_a = queue.get_status(job_id_a)
    assert status_a["state"] == "cancelled"
    assert status_a["transferred"] == 0
    assert status_a["total"] == 12
    assert status_a["final_name"] is None
    
    status_b = queue.get_status(job_id_b)
    assert status_b["state"] == "completed"
    assert status_b["transferred"] == 8
    assert status_b["total"] == 8
    assert status_b["final_name"] == "b.mp4"