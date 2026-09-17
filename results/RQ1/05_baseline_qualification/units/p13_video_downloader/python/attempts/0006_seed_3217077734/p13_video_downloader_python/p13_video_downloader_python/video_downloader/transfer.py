"""Transfer interfaces and implementations for video downloader."""

from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from .errors import TransferError, CancelledError
from .request import DownloadRequest
from .progress import Progress, CancellationToken
from .naming import sanitize_filename, unique_name


@dataclass(frozen=True)
class TransferResult:
    """Represents the result of a transfer operation."""

    bytes_transferred: int
    final_name: str
    completed: bool


class TransferAdapter:
    """Abstract base class for transfer adapters."""

    def total_bytes(self, req: DownloadRequest) -> int:
        """
        Get the total number of bytes for a download request.

        Args:
            req: The download request.

        Returns:
            The total number of bytes to transfer.

        Raises:
            TransferError: If the transfer cannot be measured.
        """
        raise NotImplementedError

    def transfer(
        self, req: DownloadRequest, progress: Progress, cancel: CancellationToken
    ) -> TransferResult:
        """
        Transfer a download request.

        Args:
            req: The download request.
            progress: The progress tracker.
            cancel: The cancellation token.

        Returns:
            The transfer result.

        Raises:
            CancelledError: If the transfer was cancelled.
            TransferError: If the transfer failed.
        """
        raise NotImplementedError


class FakeTransferAdapter(TransferAdapter):
    """A deterministic fake transfer adapter for testing."""

    def __init__(self, mapping: Dict[str, Tuple[int, int]]) -> None:
        """
        Initialize the fake transfer adapter.

        Args:
            mapping: A mapping of URLs to (total_bytes, chunk_size) tuples.
        """
        self._mapping = mapping
        self._reserved: set[str] = set()

    def total_bytes(self, req: DownloadRequest) -> int:
        """
        Get the total number of bytes for a download request.

        Args:
            req: The download request.

        Returns:
            The total number of bytes to transfer.

        Raises:
            TransferError: If the URL is not found in the mapping.
        """
        if req.url not in self._mapping:
            raise TransferError(f"No mapping for URL: {req.url}")
        return self._mapping[req.url][0]

    def transfer(
        self, req: DownloadRequest, progress: Progress, cancel: CancellationToken
    ) -> TransferResult:
        """
        Transfer a download request using simulated bytes.

        Args:
            req: The download request.
            progress: The progress tracker.
            cancel: The cancellation token.

        Returns:
            The transfer result.

        Raises:
            CancelledError: If the transfer was cancelled.
        """
        # Get the total bytes and chunk size from the mapping
        total_bytes, chunk_size = self._mapping[req.url]
        
        # Derive a sanitized base name from the output hint or URL
        if req.output_hint:
            base = sanitize_filename(req.output_hint)
        else:
            # Extract the last path segment as the base name
            from urllib.parse import urlparse
            parsed = urlparse(req.url)
            base = sanitize_filename(parsed.path.split("/")[-1])
        
        # Ensure the extension is present
        if not base.endswith(req.extension()):
            base += req.extension()
            
        # Choose a unique name
        final_name = unique_name(base, self._reserved)
        self._reserved.add(final_name)
        
        # Simulate transferring in chunks
        transferred = 0
        while transferred < total_bytes:
            # Check for cancellation before each chunk
            if cancel.is_cancelled():
                raise CancelledError("Transfer was cancelled")
                
            # Determine how much to transfer in this chunk
            remaining = total_bytes - transferred
            chunk = min(chunk_size, remaining)
            
            # Update progress
            progress.update(chunk)
            transferred += chunk
            
        # Return the transfer result
        return TransferResult(
            bytes_transferred=transferred,
            final_name=final_name,
            completed=True
        )