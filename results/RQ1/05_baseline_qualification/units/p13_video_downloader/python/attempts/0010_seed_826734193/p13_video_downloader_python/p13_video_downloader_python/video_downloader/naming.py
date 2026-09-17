"""Filename sanitization and unique naming utilities."""

import os
import re
from typing import Set


def sanitize_filename(name: str) -> str:
    """Sanitize a filename by removing invalid characters.

    Args:
        name: The raw filename string.

    Returns:
        A sanitized filename string.
    """
    if not isinstance(name, str):
        raise TypeError("Name must be a string")

    # Strip leading/trailing whitespace
    name = name.strip()

    # Replace runs of whitespace with underscores
    name = re.sub(r"\s+", "_", name)

    # Remove invalid characters (keep only letters, digits, dots, dashes, underscores)
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)

    # Trim leading/trailing dots and underscores
    name = name.strip(". _")

    # Fall back to "download" if the result is empty
    if not name:
        return "download"

    return name


def unique_name(base: str, existing: Set[str]) -> str:
    """Generate a unique filename by appending (1), (2), etc. if needed.

    Args:
        base: The base filename.
        existing: A set of existing filenames.

    Returns:
        A unique filename that doesn't exist in the existing set.
    """
    if not isinstance(base, str):
        raise TypeError("Base must be a string")
    
    if not isinstance(existing, set):
        raise TypeError("Existing must be a set")

    if base not in existing:
        return base

    # Split the base into name and extension
    name, ext = os.path.splitext(base)

    # Find the next available number
    i = 1
    while True:
        new_name = f"{name} ({i}){ext}"
        if new_name not in existing:
            return new_name
        i += 1