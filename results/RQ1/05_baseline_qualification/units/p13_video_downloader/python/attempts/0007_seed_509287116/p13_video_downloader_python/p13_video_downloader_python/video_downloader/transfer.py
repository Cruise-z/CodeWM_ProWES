"""Transfer interfaces and offline deterministic adapter for video downloader."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
from .errors import TransferError, CancelledError
from .request import DownloadRequest
from .progress import Progress
from .naming import sanitize_filename, unique_name


@dataclass(frozen=True)
class TransferResult:
    """Result of a transfer operation."""

    bytes_transferred: int
    final_name: str
    completed: bool


class TransferAdapter(ABC):
    """Abstract base class for transfer adapters."""

    @abstractmethod
    def total_bytes(self, req: DownloadRequest) -> int:
        """
        Get the total number of bytes for a download request.

        Args:
            req: The download request.

        Returns:
            The total number of bytes to transfer.

        Raises:
            TransferError: If the request cannot be processed.
        """
        pass

    @abstractmethod
    def transfer(
        self, req: DownloadRequest, progress: Progress, cancel: "CancellationToken"
    ) -> TransferResult:
        """
        Transfer a download request.

        Args:
            req: The download request.
            progress: Progress tracker to update.
            cancel: Cancellation token to check.

        Returns:
            The transfer result.

        Raises:
            CancelledError: If the transfer is cancelled.
            TransferError: If the transfer fails.
        """
        pass


class FakeTransferAdapter(TransferAdapter):
    """Deterministic fake transfer adapter for testing."""

    def __init__(self, mapping: Dict[str, Tuple[int, int]]) -> None:
        """
        Initialize the fake transfer adapter.

        Args:
            mapping: Dictionary mapping URLs to (total_bytes, chunk_size) tuples.
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
        self, req: DownloadRequest, progress: Progress, cancel: "CancellationToken"
    ) -> TransferResult:
        """
        Transfer a download request.

        Args:
            req: The download request.
            progress: Progress tracker to update.
            cancel: Cancellation token to check.

        Returns:
            The transfer result.

        Raises:
            CancelledError: If the transfer is cancelled.
            TransferError: If the transfer fails.
        """
        # Derive a sanitized base name from output_hint or URL
        if req.output_hint:
            base = sanitize_filename(req.output_hint)
        else:
            # Extract the last path segment from the URL
            url_path = req.url.split("/")[-1]
            base = sanitize_filename(url_path)
        
        # Add the extension if not present
        if not base.endswith(req.extension()):
            base += req.extension()
        
        # Choose a unique name
        final_name = unique_name(base, self._reserved)
        self._reserved.add(final_name)
        
        # Get the total bytes and chunk size from mapping
        total_bytes, chunk_size = self._mapping[req.url]
        
        # Simulate the transfer in chunks
        transferred = 0
        while transferred < total_bytes:
            # Check for cancellation before each chunk
            if cancel.is_cancelled():
                raise CancelledError("Transfer was cancelled")
            
            # Determine chunk size
            remaining = total_bytes - transferred
            actual_chunk_size = min(chunk_size, remaining)
            
            # Update progress
            progress.update(actual_chunk_size)
            transferred += actual_chunk_size
        
        return TransferResult(
            bytes_transferred=transferred,
            final_name=final_name,
            completed=True
        )