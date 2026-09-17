"""URL validation utilities."""

import urllib.parse


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
        raise InvalidURLError("URL must be a string")

    # Strip only surrounding whitespace
    stripped = url.strip()
    if not stripped:
        raise InvalidURLError("URL cannot be empty or only whitespace")

    # Reject URLs with embedded whitespace
    if any(c.isspace() for c in stripped):
        raise InvalidURLError("URL cannot contain embedded whitespace")

    # Parse the URL
    parsed = urllib.parse.urlparse(stripped)

    # Check scheme
    if parsed.scheme not in ("http", "https"):
        raise InvalidURLError("URL must have http or https scheme")

    # Check netloc
    if not parsed.netloc:
        raise InvalidURLError("URL must have a network location")

    # Check path
    if not parsed.path:
        raise InvalidURLError("URL must have a path")

    return stripped