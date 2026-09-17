"""Transfer adapter interface and fake implementation for video downloader."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
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
            TransferError: If the transfer cannot be measured.
        """

    @abstractmethod
    def transfer(
        self, req: DownloadRequest, progress: Progress, cancel: CancellationToken
    ) -> TransferResult:
        """
        Transfer data for a download request.

        Args:
            req: The download request.
            progress: The progress tracker.
            cancel: The cancellation token.

        Returns:
            The transfer result.

        Raises:
            CancelledError: If the transfer was cancelled.
            TransferError: If the transfer fails.
        """


class FakeTransferAdapter(TransferAdapter):
    """A fake transfer adapter that simulates transfers without I/O."""

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
        Get the total number of bytes for a download request.

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
        Simulate transferring data for a download request.

        Args:
            req: The download request.
            progress: The progress tracker.
            cancel: The cancellation token.

        Returns:
            The transfer result.

        Raises:
            CancelledError: If the transfer was cancelled.
        """
        # Derive base name from output_hint or URL
        if req.output_hint is not None:
            base = req.output_hint
        else:
            # Extract the last segment of the URL path
            url_path = req.url.split("/")[-1]
            # If URL ends with a slash, fallback to "download"
            if not url_path:
                base = "download"
            else:
                base = url_path

        # Ensure extension is present
        if not base.endswith(req.extension()):
            base += req.extension()

        # Generate unique name
        final_name = unique_name(base, self._reserved)

        # Mark name as reserved
        self._reserved.add(final_name)

        # Get transfer parameters
        total_bytes, chunk_size = self._mapping[req.url]

        # Simulate transfer in chunks
        transferred = 0
        while transferred < total_bytes:
            # Check for cancellation before each chunk
            if cancel.is_cancelled():
                # Clean up reservation on cancellation
                self._reserved.discard(final_name)
                raise CancelledError("Transfer was cancelled")

            # Determine chunk size for this iteration
            remaining = total_bytes - transferred
            actual_chunk_size = min(chunk_size, remaining)

            # Update progress
            progress.update(actual_chunk_size)
            transferred += actual_chunk_size

        # Return result
        return TransferResult(
            bytes_transferred=transferred,
            final_name=final_name,
            completed=True,
        )