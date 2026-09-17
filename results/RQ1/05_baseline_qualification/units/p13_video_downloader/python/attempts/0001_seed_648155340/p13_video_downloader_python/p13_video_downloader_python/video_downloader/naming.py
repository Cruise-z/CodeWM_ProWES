"""Filename sanitation and unique naming utilities for video downloader."""

import os
import re
from typing import Set


def sanitize_filename(name: str) -> str:
    """
    Sanitize a filename by removing/disallowing problematic characters.

    Args:
        name: The raw filename string.

    Returns:
        A sanitized filename string.
    """
    if not isinstance(name, str):
        raise TypeError("Filename must be a string")

    # Strip leading/trailing whitespace
    name = name.strip()

    # Replace runs of whitespace with underscores
    name = re.sub(r"\s+", "_", name)

    # Remove path separators and characters outside letters/digits/dot/dash/underscore
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)

    # Trim leading/trailing dots and underscores
    name = name.strip(". _")

    # Fall back to "download" if empty
    if not name:
        return "download"

    return name


def unique_name(base: str, existing: Set[str]) -> str:
    """
    Generate a unique filename by appending (1), (2), etc. if needed.

    Args:
        base: The base filename.
        existing: A set of already-used filenames.

    Returns:
        A unique filename that is not in the existing set.
    """
    if base not in existing:
        return base

    # Split basename and extension
    name, ext = os.path.splitext(base)
    
    # Start trying from 1
    counter = 1
    while True:
        new_name = f"{name} ({counter}){ext}"
        if new_name not in existing:
            return new_name
        counter += 1