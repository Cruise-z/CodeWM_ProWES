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
    """Test that the demo completes with correct status."""
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


def test_synchronous_cancellation():
    """Test synchronous cancellation fixture."""
    # Create a fake transfer adapter with mappings
    mapping = {
        "https://example.com/a": (12, 4),
        "https://example.com/b": (8, 4),
    }
    adapter = FakeTransferAdapter(mapping)
    
    # Create a download queue
    queue = DownloadQueue(adapter)
    
    # Create two download requests
    req_a = DownloadRequest("https://example.com/a", "mp4")
    req_b = DownloadRequest("https://example.com/b", "mp4")
    
    # Enqueue both requests
    job_id_a = queue.enqueue(req_a)
    job_id_b = queue.enqueue(req_b)
    
    # Cancel the first job before processing
    assert queue.cancel(job_id_a) == True
    
    # Process all jobs
    queue.process_all()
    
    # Check first job status (should be cancelled)
    status_a = queue.get_status(job_id_a)
    assert status_a["state"] == "cancelled"
    assert status_a["transferred"] == 0
    assert status_a["total"] == 12
    
    # Check second job status (should be completed)
    status_b = queue.get_status(job_id_b)
    assert status_b["state"] == "completed"
    assert status_b["transferred"] == 8
    assert status_b["total"] == 8
    assert status_b["final_name"] == "b.mp4"