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


def test_demo_completes_12_12():
    """Test that run_demo returns a completed status with 12/12 transferred."""
    result = run_demo()
    assert result["state"] == "completed"
    assert result["transferred"] == 12
    assert result["total"] == 12
    assert result["final_name"] == "clip.mp4"


def test_url_and_format_validation():
    """Test URL and format validation errors."""
    # Test valid URL
    assert validate_url(" https://example.com/video ") == "https://example.com/video"
    
    # Test invalid URLs
    try:
        validate_url("ftp://example.com/video")
        assert False, "Should have raised InvalidURLError"
    except InvalidURLError:
        pass  # Expected
    
    try:
        validate_url("")
        assert False, "Should have raised InvalidURLError"
    except InvalidURLError:
        pass  # Expected
    
    try:
        validate_url("https://example.com/video with spaces")
        assert False, "Should have raised InvalidURLError"
    except InvalidURLError:
        pass  # Expected
    
    # Test valid formats
    req = DownloadRequest("https://example.com/video", "mp4")
    assert req.fmt == "mp4"
    
    req = DownloadRequest("https://example.com/video", "WEBM")
    assert req.fmt == "webm"
    
    # Test invalid format
    try:
        DownloadRequest("https://example.com/video", "avi")
        assert False, "Should have raised InvalidFormatError"
    except InvalidFormatError:
        pass  # Expected


def test_naming_fixtures():
    """Test naming fixtures."""
    assert sanitize_filename("my clip") == "my_clip"
    assert unique_name("clip.mp4", {"clip.mp4"}) == "clip (1).mp4"


def test_queue_pre_start_cancellation():
    """Test synchronous queue pre-start cancellation fixture."""
    # Create mapping for two jobs
    mapping = {
        "https://example.com/a": (12, 4),
        "https://example.com/b": (8, 4)
    }
    
    # Create adapter and queue
    adapter = FakeTransferAdapter(mapping)
    queue = DownloadQueue(adapter)
    
    # Enqueue two requests
    req_a = DownloadRequest("https://example.com/a", "mp4")
    req_b = DownloadRequest("https://example.com/b", "mp4")
    
    job_a_id = queue.enqueue(req_a)
    job_b_id = queue.enqueue(req_b)
    
    # Cancel first job before processing
    assert queue.cancel(job_a_id) == True
    
    # Process all jobs
    queue.process_all()
    
    # Check first job status (should be cancelled)
    status_a = queue.get_status(job_a_id)
    assert status_a["state"] == "cancelled"
    assert status_a["transferred"] == 0
    assert status_a["total"] == 12
    
    # Check second job status (should be completed)
    status_b = queue.get_status(job_b_id)
    assert status_b["state"] == "completed"
    assert status_b["transferred"] == 8
    assert status_b["total"] == 8
    assert status_b["final_name"] == "b.mp4"