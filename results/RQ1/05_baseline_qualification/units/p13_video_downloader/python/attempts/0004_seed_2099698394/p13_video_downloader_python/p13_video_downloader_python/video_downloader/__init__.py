"""Public API re-exports for the video downloader package."""

# Exceptions
from .errors import (
    InvalidURLError,
    InvalidFormatError,
    TransferError,
    CancelledError,
)

# URL utilities
from .url import validate_url

# Naming utilities
from .naming import sanitize_filename, unique_name

# Domain entities
from .request import DownloadRequest
from .progress import Progress, CancellationToken

# Transfer interfaces
from .transfer import (
    TransferAdapter,
    TransferResult,
    FakeTransferAdapter,
)

# Queue management
from .queue import DownloadQueue

# Explicitly define what is exported
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