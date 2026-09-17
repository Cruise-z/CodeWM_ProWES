"""Public API re-exports for video downloader."""

# Re-export foundational exceptions
from .errors import (
    InvalidURLError,
    InvalidFormatError,
    TransferError,
    CancelledError,
)

# Re-export utility functions
from .url import validate_url
from .naming import sanitize_filename, unique_name

# Re-export domain entities
from .request import DownloadRequest
from .progress import Progress, CancellationToken

# Re-export transfer interfaces
from .transfer import TransferAdapter, TransferResult, FakeTransferAdapter

# Re-export queue
from .queue import DownloadQueue