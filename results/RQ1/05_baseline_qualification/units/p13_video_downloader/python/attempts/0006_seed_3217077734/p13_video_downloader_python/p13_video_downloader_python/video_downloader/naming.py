"""Filename sanitation and unique naming utilities for video downloader."""

import re
import os
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
        name = str(name)

    # Strip leading/trailing whitespace
    name = name.strip()

    # Replace sequences of whitespace with underscores
    name = re.sub(r"\s+", "_", name)

    # Remove path separators and invalid characters
    name = re.sub(r'[<>:"/\\|?*]', "", name)

    # Remove control characters
    name = "".join(char for char in name if ord(char) >= 32 and char != "\x7f")

    # Trim leading/trailing dots and underscores
    name = name.strip(". _")

    # Fall back to "download" if the result is empty or all dots/underscores
    if not name or all(c in "._" for c in name):
        return "download"

    return name


def unique_name(base: str, existing: Set[str]) -> str:
    """
    Generate a unique filename by appending (1), (2), etc. if needed.

    Args:
        base: The base filename.
        existing: A set of existing filenames.

    Returns:
        A unique filename that doesn't conflict with existing names.
    """
    if base not in existing:
        return base

    # Split the base into name and extension
    name, ext = os.path.splitext(base)
    counter = 1

    # Keep trying new names until we find one that's not taken
    while True:
        new_name = f"{name} ({counter}){ext}"
        if new_name not in existing:
            return new_name
        counter += 1