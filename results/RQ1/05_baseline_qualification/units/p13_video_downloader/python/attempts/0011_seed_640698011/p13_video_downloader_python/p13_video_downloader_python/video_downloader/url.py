"""URL validation utilities for video downloader."""

import urllib.parse


def validate_url(url: str) -> str:
    """
    Validate a URL string.

    Args:
        url: The URL string to validate.

    Returns:
        The validated URL string with surrounding whitespace stripped.

    Raises:
        InvalidURLError: If the URL is invalid.
    """
    if not isinstance(url, str):
        raise InvalidURLError("URL must be a string")

    # Strip surrounding whitespace only
    stripped = url.strip()
    if not stripped:
        raise InvalidURLError("URL cannot be empty or only whitespace")

    # Check for embedded whitespace
    if any(char.isspace() for char in url):
        raise InvalidURLError("URL cannot contain embedded whitespace")

    # Parse the URL
    parsed = urllib.parse.urlparse(stripped)

    # Check scheme
    if parsed.scheme not in ("http", "https"):
        raise InvalidURLError("URL must have http or https scheme")

    # Check netloc and path
    if not parsed.netloc:
        raise InvalidURLError("URL must have a network location")
    if not parsed.path:
        raise InvalidURLError("URL must have a path")

    return stripped