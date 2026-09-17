"""Filename sanitation and unique naming utilities for video downloader."""

import os
import re
from typing import Set


def sanitize_filename(name: str) -> str:
    """
    Sanitize a filename by replacing invalid characters.

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

    # Remove path separators and invalid characters
    name = re.sub(r'[<>:"/\\|?*]', "", name)

    # Remove control characters
    name = "".join(char for char in name if ord(char) >= 32 and char != "\x7f")

    # Trim leading/trailing dots and underscores
    name = name.strip("._")

    # Fall back to "download" if the name is empty after sanitization
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
        A unique filename that is not in the existing set.
    """
    if not isinstance(base, str):
        raise TypeError("Base must be a string")
    if not isinstance(existing, set):
        raise TypeError("Existing must be a set")

    if base not in existing:
        return base

    # Split the base into name and extension
    name, ext = os.path.splitext(base)
    counter = 1
    new_name = f"{name} ({counter}){ext}"

    while new_name in existing:
        counter += 1
        new_name = f"{name} ({counter}){ext}"

    return new_name