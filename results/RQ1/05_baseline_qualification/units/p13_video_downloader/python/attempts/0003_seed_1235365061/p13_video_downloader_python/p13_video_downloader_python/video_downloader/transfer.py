"""Transfer interfaces and offline deterministic adapter for video downloader."""

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
            TransferError: If the total bytes cannot be determined.
        """
        pass

    @abstractmethod
    def transfer(
        self, req: DownloadRequest, progress: Progress, cancel: CancellationToken
    ) -> TransferResult:
        """
        Transfer data for a download request.

        Args:
            req: The download request.
            progress: Progress tracker to update during transfer.
            cancel: Cancellation token to check for cancellation.

        Returns:
            The transfer result.

        Raises:
            CancelledError: If the transfer is cancelled.
            TransferError: If the transfer fails.
        """
        pass


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
            raise TransferError(f"No mapping found for URL: {req.url}")
        return self._mapping[req.url][0]

    def transfer(
        self, req: DownloadRequest, progress: Progress, cancel: CancellationToken
    ) -> TransferResult:
        """
        Simulate transferring data for a download request.

        Args:
            req: The download request.
            progress: Progress tracker to update during transfer.
            cancel: Cancellation token to check for cancellation.

        Returns:
            The transfer result.

        Raises:
            CancelledError: If the transfer is cancelled.
            TransferError: If the transfer fails.
        """
        if req.url not in self._mapping:
            raise TransferError(f"No mapping found for URL: {req.url}")

        total_bytes, chunk_size = self._mapping[req.url]

        # Derive base name from output_hint or URL's final path segment
        if req.output_hint:
            base_name = sanitize_filename(req.output_hint)
        else:
            # Extract last segment of URL path
            url_path = req.url.split("/")[-1]
            base_name = sanitize_filename(url_path)

        # Add extension if not present
        if not base_name.endswith(req.extension()):
            base_name += req.extension()

        # Choose unique name
        final_name = unique_name(base_name, self._reserved)
        self._reserved.add(final_name)

        # Simulate transfer in chunks
        transferred = 0
        while transferred < total_bytes:
            if cancel.is_cancelled():
                raise CancelledError("Transfer was cancelled")

            # Determine chunk size (can't exceed remaining bytes)
            current_chunk_size = min(chunk_size, total_bytes - transferred)
            transferred += current_chunk_size
            progress.update(current_chunk_size)

        return TransferResult(
            bytes_transferred=transferred, final_name=final_name, completed=True
        )