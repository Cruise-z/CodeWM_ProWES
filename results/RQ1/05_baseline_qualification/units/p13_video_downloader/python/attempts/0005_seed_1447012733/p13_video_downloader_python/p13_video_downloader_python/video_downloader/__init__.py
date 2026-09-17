"""Public API re-exports for the video downloader package."""

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

# Re-export transfer interfaces and implementations
from .transfer import TransferAdapter, TransferResult, FakeTransferAdapter

# Re-export orchestration components
from .queue import DownloadQueue