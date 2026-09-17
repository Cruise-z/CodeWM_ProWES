"""Download request entity with validation and format handling."""

import os
from typing import Optional
from .errors import InvalidFormatError
from .url import validate_url


class DownloadRequest:
    """A download request with URL, format, and output hint."""

    def __init__(
        self, url: str, fmt: str, output_hint: Optional[str] = None
    ) -> None:
        """
        Initialize a download request.

        Args:
            url: The URL to download.
            fmt: The desired format (mp4, webm, mkv).
            output_hint: Optional hint for the output filename.

        Raises:
            InvalidURLError: If the URL is invalid.
            InvalidFormatError: If the format is not supported.
        """
        self._url = validate_url(url)
        self._fmt = fmt.lower()
        
        # Validate format
        if self._fmt not in ("mp4", "webm", "mkv"):
            raise InvalidFormatError(
                f"Unsupported format: {fmt}. Supported formats are mp4, webm, mkv."
            )
        
        # Store sanitized output hint if provided
        if output_hint is not None:
            from .naming import sanitize_filename
            self._output_hint = sanitize_filename(output_hint)
        else:
            self._output_hint = None

    @property
    def url(self) -> str:
        """Get the URL."""
        return self._url

    @property
    def fmt(self) -> str:
        """Get the format."""
        return self._fmt

    @property
    def output_hint(self) -> Optional[str]:
        """Get the output hint."""
        return self._output_hint

    def extension(self) -> str:
        """
        Get the file extension for this request.

        Returns:
            The file extension including the dot.
        """
        return f".{self._fmt}"