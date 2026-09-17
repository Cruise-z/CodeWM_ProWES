"""URL validation utilities for video downloader."""

import urllib.parse


def validate_url(url: str) -> str:
    """Validate a URL string.

    Args:
        url: The URL string to validate.

    Returns:
        The validated URL string with surrounding whitespace stripped.

    Raises:
        InvalidURLError: If the URL is invalid.
    """
    if not isinstance(url, str):
        raise InvalidURLError("URL must be a string")

    # Strip surrounding whitespace
    stripped_url = url.strip()

    # Check for empty string after stripping
    if not stripped_url:
        raise InvalidURLError("URL cannot be empty")

    # Parse the URL
    parsed = urllib.parse.urlparse(stripped_url)

    # Check for valid scheme
    if parsed.scheme not in ("http", "https"):
        raise InvalidURLError(
            f"URL must have http or https scheme, got {parsed.scheme}"
        )

    # Check for non-empty netloc
    if not parsed.netloc:
        raise InvalidURLError("URL must have a non-empty network location")

    # Check for non-empty path
    if not parsed.path:
        raise InvalidURLError("URL must have a non-empty path")

    # Check for embedded whitespace
    if " " in stripped_url:
        raise InvalidURLError("URL cannot contain embedded whitespace")

    return stripped_url