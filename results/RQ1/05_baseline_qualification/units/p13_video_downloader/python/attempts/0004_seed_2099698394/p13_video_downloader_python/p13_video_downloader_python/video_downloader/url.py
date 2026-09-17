"""URL validation utilities."""

import urllib.parse


def validate_url(url: str) -> str:
    """
    Validate a URL string.

    Args:
        url: The URL string to validate.

    Returns:
        The validated and stripped URL.

    Raises:
        InvalidURLError: If the URL is invalid.
    """
    if not isinstance(url, str):
        raise InvalidURLError("URL must be a string")

    # Strip surrounding whitespace
    stripped_url = url.strip()

    # Check for embedded whitespace
    if any(char.isspace() for char in stripped_url):
        raise InvalidURLError("URL must not contain embedded whitespace")

    # Parse the URL
    parsed = urllib.parse.urlparse(stripped_url)

    # Check scheme
    if parsed.scheme not in ("http", "https"):
        raise InvalidURLError("URL must have http or https scheme")

    # Check netloc and path
    if not parsed.netloc:
        raise InvalidURLError("URL must have a non-empty network location")
    if not parsed.path:
        raise InvalidURLError("URL must have a non-empty path")

    return stripped_url