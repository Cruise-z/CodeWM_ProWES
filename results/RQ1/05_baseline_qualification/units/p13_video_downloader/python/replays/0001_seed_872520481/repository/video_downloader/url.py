"""URL validation utilities."""

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
    
    # Check for embedded whitespace
    if any(char.isspace() for char in stripped):
        raise InvalidURLError("URL cannot contain embedded whitespace")
    
    # Parse the URL
    parsed = urllib.parse.urlparse(stripped)
    
    # Check scheme
    if parsed.scheme not in ("http", "https"):
        raise InvalidURLError("URL must use http or https scheme")
    
    # Check netloc and path
    if not parsed.netloc:
        raise InvalidURLError("URL must have a non-empty netloc")
    
    if not parsed.path:
        raise InvalidURLError("URL must have a non-empty path")
    
    return stripped