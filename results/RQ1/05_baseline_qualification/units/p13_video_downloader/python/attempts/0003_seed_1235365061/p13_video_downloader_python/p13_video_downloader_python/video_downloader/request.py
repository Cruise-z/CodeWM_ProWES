"""Download request domain entity for video downloader."""

from typing import Optional
from .errors import InvalidFormatError
from .url import validate_url


class DownloadRequest:
    """A download request with URL, format, and optional output hint."""

    def __init__(
        self, url: str, fmt: str, output_hint: Optional[str] = None
    ) -> None:
        """
        Initialize a download request.

        Args:
            url: The URL to download from.
            fmt: The desired format (mp4, webm, mkv).
            output_hint: Optional hint for the output filename.

        Raises:
            InvalidURLError: If the URL is invalid.
            InvalidFormatError: If the format is not supported.
        """
        self._url = validate_url(url)
        self._fmt = fmt.lower()
        valid_formats = {"mp4", "webm", "mkv"}
        if self._fmt not in valid_formats:
            raise InvalidFormatError(
                f"Unsupported format: {fmt}. Supported formats are {valid_formats}"
            )
        self._output_hint = output_hint
        self._extension = f".{self._fmt}"

    @property
    def url(self) -> str:
        """Get the download URL."""
        return self._url

    @property
    def fmt(self) -> str:
        """Get the requested format."""
        return self._fmt

    @property
    def output_hint(self) -> Optional[str]:
        """Get the output filename hint."""
        return self._output_hint

    def extension(self) -> str:
        """
        Get the file extension for this request.

        Returns:
            The file extension including the dot.
        """
        return self._extension