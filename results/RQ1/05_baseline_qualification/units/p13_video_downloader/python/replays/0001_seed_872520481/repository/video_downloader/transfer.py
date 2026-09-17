"""Transfer interfaces and offline deterministic adapter."""

from typing import Dict, Tuple, Optional
from dataclasses import dataclass
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
    """Abstract interface for transfer operations."""

    @abstractmethod
    def total_bytes(self, req: DownloadRequest) -> int:
        """
        Get the total number of bytes for a request.

        Args:
            req: The download request.

        Returns:
            The total number of bytes to transfer.

        Raises:
            TransferError: If the transfer cannot be performed.
        """
        pass

    @abstractmethod
    def transfer(
        self, req: DownloadRequest, progress: Progress, cancel: CancellationToken
    ) -> TransferResult:
        """
        Transfer a request.

        Args:
            req: The download request.
            progress: Progress tracker.
            cancel: Cancellation token.

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
            mapping: A dictionary mapping URLs to (total_bytes, chunk_size) tuples.
        """
        self._mapping = mapping
        self._reserved: set[str] = set()

    def total_bytes(self, req: DownloadRequest) -> int:
        """
        Get the total bytes for a request.

        Args:
            req: The download request.

        Returns:
            The total number of bytes to transfer.

        Raises:
            TransferError: If the URL is not found in the mapping.
        """
        if req.url not in self._mapping:
            raise TransferError(f"No transfer mapping for URL: {req.url}")
        return self._mapping[req.url][0]

    def transfer(
        self, req: DownloadRequest, progress: Progress, cancel: CancellationToken
    ) -> TransferResult:
        """
        Simulate transferring a request in fixed chunks.

        Args:
            req: The download request.
            progress: Progress tracker.
            cancel: Cancellation token.

        Returns:
            The transfer result.

        Raises:
            CancelledError: If the transfer is cancelled.
            TransferError: If the transfer fails.
        """
        if req.url not in self._mapping:
            raise TransferError(f"No transfer mapping for URL: {req.url}")

        total_bytes, chunk_size = self._mapping[req.url]
        
        # Derive a base name from output_hint or URL
        if req.output_hint:
            base = sanitize_filename(req.output_hint)
        else:
            # Extract filename from URL path
            from urllib.parse import urlparse
            parsed = urlparse(req.url)
            base = sanitize_filename(parsed.path.split("/")[-1])
            
        # Ensure extension is present
        if not base.endswith(req.extension()):
            base += req.extension()
            
        # Choose unique name
        final_name = unique_name(base, self._reserved)
        self._reserved.add(final_name)
        
        # Simulate transfer in chunks
        transferred = 0
        while transferred < total_bytes:
            if cancel.is_cancelled():
                raise CancelledError("Transfer was cancelled")
                
            # Determine chunk size
            remaining = total_bytes - transferred
            current_chunk = min(chunk_size, remaining)
            
            # Update progress
            progress.update(current_chunk)
            transferred += current_chunk
            
        return TransferResult(
            bytes_transferred=total_bytes,
            final_name=final_name,
            completed=True
        )