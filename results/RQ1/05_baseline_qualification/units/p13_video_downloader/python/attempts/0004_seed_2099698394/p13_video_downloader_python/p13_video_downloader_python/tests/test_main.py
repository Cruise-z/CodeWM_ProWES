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


def test_run_demo():
    """Test that run_demo returns correct status for completed download."""
    result = run_demo()
    assert result["state"] == "completed"
    assert result["transferred"] == 12
    assert result["total"] == 12
    assert result["final_name"] == "clip.mp4"


def test_url_and_format_validation():
    """Test URL and format validation errors."""
    # Test valid URL
    assert validate_url(" https://example.com/file ") == "https://example.com/file"
    
    # Test invalid URLs
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
    
    # Test valid formats
    req = DownloadRequest("https://example.com/file", "mp4")
    assert req.fmt == "mp4"
    
    req = DownloadRequest("https://example.com/file", "WEBM")
    assert req.fmt == "webm"
    
    # Test invalid format
    try:
        DownloadRequest("https://example.com/file", "avi")
        assert False, "Should have raised InvalidFormatError"
    except InvalidFormatError:
        pass  # Expected


def test_naming_utilities():
    """Test filename sanitization and uniqueness."""
    assert sanitize_filename("my clip") == "my_clip"
    assert unique_name("clip.mp4", {"clip.mp4"}) == "clip (1).mp4"


def test_queue_cancellation():
    """Test synchronous queue cancellation before processing."""
    # Create mapping for two jobs
    mapping = {
        "https://example.com/a": (12, 4),
        "https://example.com/b": (8, 4)
    }
    
    # Create adapter and queue
    adapter = FakeTransferAdapter(mapping)
    queue = DownloadQueue(adapter)
    
    # Enqueue both jobs
    job_a_id = queue.enqueue(DownloadRequest("https://example.com/a", "mp4"))
    job_b_id = queue.enqueue(DownloadRequest("https://example.com/b", "mp4"))
    
    # Cancel the first job before processing
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