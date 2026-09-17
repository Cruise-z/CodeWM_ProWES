"""URL validation utilities for video downloader."""

import urllib.parse
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
        raise InvalidURLError("URL must be a string")

    # Strip surrounding whitespace
    stripped = url.strip()
    
    # Reject if empty after stripping
    if not stripped:
        raise InvalidURLError("URL cannot be empty")
    
    # Reject if contains embedded whitespace
    if any(c.isspace() for c in stripped):
        raise InvalidURLError("URL cannot contain embedded whitespace")
    
    # Parse the URL
    parsed = urllib.parse.urlparse(stripped)
    
    # Must have http or https scheme
    if parsed.scheme not in ("http", "https"):
        raise InvalidURLError("URL must have http or https scheme")
    
    # Must have non-empty netloc
    if not parsed.netloc:
        raise InvalidURLError("URL must have a non-empty network location")
    
    # Must have non-empty path
    if not parsed.path:
        raise InvalidURLError("URL must have a non-empty path")
    
    return stripped