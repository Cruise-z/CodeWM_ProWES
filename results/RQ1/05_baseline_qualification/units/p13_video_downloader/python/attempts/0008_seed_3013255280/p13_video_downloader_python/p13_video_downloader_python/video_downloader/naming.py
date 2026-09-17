"""Safe filename sanitation and deterministic unique naming."""

import os
import re
from typing import Set


def sanitize_filename(name: str) -> str:
    """
    Sanitize a filename by replacing invalid characters.

    Args:
        name: The raw filename string.

    Returns:
        A sanitized filename safe for use in filesystem operations.
    """
    if not isinstance(name, str):
        raise TypeError("Filename must be a string")

    # Strip leading/trailing whitespace
    name = name.strip()

    # Replace sequences of whitespace with underscore
    name = re.sub(r"\s+", "_", name)

    # Remove path separators and invalid characters
    name = re.sub(r'[<>:"/\\|?*]', "", name)

    # Trim leading/trailing dots and underscores
    name = name.strip(". _")

    # Fall back to "download" if empty after sanitization
    if not name:
        return "download"

    return name


def unique_name(base: str, existing: Set[str]) -> str:
    """
    Generate a unique filename by appending (1), (2), etc. if needed.

    Args:
        base: The base filename.
        existing: A set of existing filenames.

    Returns:
        A unique filename that does not exist in the existing set.
    """
    if not isinstance(base, str):
        raise TypeError("Base filename must be a string")
    
    if not isinstance(existing, set):
        raise TypeError("Existing filenames must be a set")

    if base not in existing:
        return base

    # Split basename and extension
    name_without_ext, ext = os.path.splitext(base)
    
    # Try names with increasing numbers until we find a unique one
    i = 1
    while True:
        new_name = f"{name_without_ext} ({i}){ext}"
        if new_name not in existing:
            return new_name
        i += 1