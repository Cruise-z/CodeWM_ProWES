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


def test_demo_completion() -> None:
    """Test that run_demo returns correct status for 12/12 completion."""
    result = run_demo()
    assert result["state"] == "completed"
    assert result["transferred"] == 12
    assert result["total"] == 12
    assert result["final_name"] == "clip.mp4"


def test_validation_errors() -> None:
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
    
    # Test valid URL
    assert validate_url(" https://example.com/file ") == "https://example.com/file"
    
    # Test invalid format
    try:
        DownloadRequest("https://example.com/file", "avi")
        assert False, "Should have raised InvalidFormatError"
    except InvalidFormatError:
        pass  # Expected


def test_naming_fixtures() -> None:
    """Test filename sanitization and uniqueness fixtures."""
    assert sanitize_filename("my clip") == "my_clip"
    assert unique_name("clip.mp4", {"clip.mp4"}) == "clip (1).mp4"


def test_synchronous_cancellation() -> None:
    """Test queue cancellation with pre-start cancellation fixture."""
    # Setup mapping
    mapping = {
        "a": (12, 4),  # 12 bytes total, 4 bytes per chunk
        "b": (8, 4),   # 8 bytes total, 4 bytes per chunk
    }
    
    # Create adapter and queue
    adapter = FakeTransferAdapter(mapping)
    queue = DownloadQueue(adapter)
    
    # Enqueue two requests
    req_a = DownloadRequest("a", "mp4")
    req_b = DownloadRequest("b", "mp4")
    
    id_a = queue.enqueue(req_a)
    id_b = queue.enqueue(req_b)
    
    # Cancel first job before processing
    assert queue.cancel(id_a) is True
    
    # Process all jobs
    queue.process_all()
    
    # Check results
    status_a = queue.get_status(id_a)
    status_b = queue.get_status(id_b)
    
    assert status_a["state"] == "cancelled"
    assert status_a["transferred"] == 0
    assert status_a["total"] == 12
    assert status_a["final_name"] is None
    
    assert status_b["state"] == "completed"
    assert status_b["transferred"] == 8
    assert status_b["total"] == 8
    assert status_b["final_name"] == "b.mp4"