"""URL validation utilities for video downloader."""

import re
from urllib.parse import urlparse

from .errors import InvalidURLError


def validate_url(url: str) -> str:
    """
    Validate a URL string.

    Args:
        url: The URL to validate.

    Returns:
        The validated URL string with surrounding whitespace stripped.

    Raises:
        InvalidURLError: If the URL is invalid.
    """
    if not isinstance(url, str):
        raise InvalidURLError("URL must be a string.")

    # Strip surrounding whitespace
    stripped_url = url.strip()

    # Check for empty string after stripping
    if not stripped_url:
        raise InvalidURLError("URL cannot be empty.")

    # Check for embedded whitespace
    if re.search(r"\s", stripped_url):
        raise InvalidURLError("URL cannot contain embedded whitespace.")

    # Parse the URL
    parsed = urlparse(stripped_url)

    # Check scheme
    if parsed.scheme not in ("http", "https"):
        raise InvalidURLError("URL must have http or https scheme.")

    # Check netloc
    if not parsed.netloc:
        raise InvalidURLError("URL must have a network location.")

    # Check path
    if not parsed.path:
        raise InvalidURLError("URL must have a path.")

    return stripped_url