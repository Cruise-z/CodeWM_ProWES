"""Tests for the video downloader demo and core functionality."""

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
    """Test that run_demo completes with correct status."""
    result = run_demo()
    assert result["state"] == "completed"
    assert result["transferred"] == 12
    assert result["total"] == 12
    assert result["final_name"] == "clip.mp4"


def test_validation_errors():
    """Test URL and format validation errors."""
    # Test URL validation
    assert validate_url(" https://example.com/path ") == "https://example.com/path"
    
    try:
        validate_url("ftp://example.com/path")
        assert False, "Should have raised InvalidURLError"
    except InvalidURLError:
        pass  # Expected
    
    try:
        validate_url("")
        assert False, "Should have raised InvalidURLError"
    except InvalidURLError:
        pass  # Expected
    
    # Test format validation
    try:
        DownloadRequest("https://example.com/path", "avi")
        assert False, "Should have raised InvalidFormatError"
    except InvalidFormatError:
        pass  # Expected


def test_naming_fixtures():
    """Test naming fixtures."""
    assert sanitize_filename("my clip") == "my_clip"
    assert unique_name("clip.mp4", {"clip.mp4"}) == "clip (1).mp4"


def test_queue_cancellation():
    """Test synchronous queue pre-start cancellation fixture."""
    # Create mapping for two jobs
    mapping = {"a": (12, 4), "b": (8, 4)}
    adapter = FakeTransferAdapter(mapping)
    queue = DownloadQueue(adapter)
    
    # Enqueue two requests
    req_a = DownloadRequest("a", "mp4")
    req_b = DownloadRequest("b", "mp4")
    
    job_a_id = queue.enqueue(req_a)
    job_b_id = queue.enqueue(req_b)
    
    # Cancel the first job before processing
    assert queue.cancel(job_a_id) == True
    
    # Process all jobs
    queue.process_all()
    
    # Check first job status (should be cancelled)
    status_a = queue.get_status(job_a_id)
    assert status_a["state"] == "cancelled"
    assert status_a["transferred"] == 0
    assert status_a["total"] == 12
    assert status_a["final_name"] is None
    
    # Check second job status (should be completed)
    status_b = queue.get_status(job_b_id)
    assert status_b["state"] == "completed"
    assert status_b["transferred"] == 8
    assert status_b["total"] == 8
    assert status_b["final_name"] == "b.mp4"