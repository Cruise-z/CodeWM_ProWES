"""Transfer interfaces and fake implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple, Optional
from abc import ABC, abstractmethod

from .errors import TransferError, CancelledError
from .request import DownloadRequest
from .progress import Progress, CancellationToken
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
        """Get the total number of bytes for a download request.

        Args:
            req: The download request.

        Returns:
            The total number of bytes to transfer.

        Raises:
            TransferError: If the transfer cannot be started.
        """

    @abstractmethod
    def transfer(
        self, req: DownloadRequest, progress: Progress, cancel: CancellationToken
    ) -> TransferResult:
        """Transfer a download request.

        Args:
            req: The download request.
            progress: The progress tracker.
            cancel: The cancellation token.

        Returns:
            The transfer result.

        Raises:
            CancelledError: If the transfer is cancelled.
            TransferError: If the transfer fails.
        """


class FakeTransferAdapter(TransferAdapter):
    """A fake transfer adapter that simulates transfers without I/O."""

    def __init__(self, mapping: Dict[str, Tuple[int, int]]) -> None:
        """Initialize the fake transfer adapter.

        Args:
            mapping: A mapping of URLs to (total_bytes, chunk_size) tuples.
        """
        self._mapping = mapping
        self._reserved: set[str] = set()

    def total_bytes(self, req: DownloadRequest) -> int:
        """Get the total bytes for a request.

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
        """Simulate a transfer.

        Args:
            req: The download request.
            progress: The progress tracker.
            cancel: The cancellation token.

        Returns:
            The transfer result.

        Raises:
            CancelledError: If the transfer is cancelled.
        """
        # Get the total bytes and chunk size
        total_bytes, chunk_size = self._mapping[req.url]
        
        # Derive a sanitized base name from the output hint or URL
        if req.output_hint:
            base_name = sanitize_filename(req.output_hint)
        else:
            # Extract the final path segment from the URL
            from urllib.parse import urlparse
            parsed = urlparse(req.url)
            base_name = sanitize_filename(parsed.path.split("/")[-1])
            
        # Add the extension if not present
        if not base_name.endswith(req.extension()):
            base_name += req.extension()
            
        # Choose a unique name
        final_name = unique_name(base_name, self._reserved)
        self._reserved.add(final_name)
        
        # Simulate the transfer in chunks
        transferred = 0
        while transferred < total_bytes:
            # Check for cancellation
            if cancel.is_cancelled():
                raise CancelledError("Transfer was cancelled")
                
            # Determine chunk size
            remaining = total_bytes - transferred
            actual_chunk_size = min(chunk_size, remaining)
            
            # Update progress
            progress.update(actual_chunk_size)
            transferred += actual_chunk_size
            
        # Return the result
        return TransferResult(
            bytes_transferred=transferred,
            final_name=final_name,
            completed=True
        )