"""Public API for video downloader."""

from .errors import InvalidURLError, InvalidFormatError, TransferError, CancelledError
from .url import validate_url
from .naming import sanitize_filename, unique_name
from .request import DownloadRequest
from .progress import Progress, CancellationToken
from .transfer import TransferAdapter, TransferResult, FakeTransferAdapter
from .queue import DownloadQueue

__all__ = [
    "InvalidURLError",
    "InvalidFormatError",
    "TransferError",
    "CancelledError",
    "validate_url",
    "sanitize_filename",
    "unique_name",
    "DownloadRequest",
    "Progress",
    "CancellationToken",
    "TransferAdapter",
    "TransferResult",
    "FakeTransferAdapter",
    "DownloadQueue",
]