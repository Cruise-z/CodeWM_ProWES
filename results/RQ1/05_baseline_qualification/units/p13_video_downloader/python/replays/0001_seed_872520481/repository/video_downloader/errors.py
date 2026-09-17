"""Domain exceptions for video downloader."""

class InvalidURLError(ValueError):
    """Raised when a URL is invalid."""

class InvalidFormatError(ValueError):
    """Raised when a format is invalid."""

class TransferError(RuntimeError):
    """Raised when a transfer operation fails."""

class CancelledError(RuntimeError):
    """Raised when a transfer is cancelled."""