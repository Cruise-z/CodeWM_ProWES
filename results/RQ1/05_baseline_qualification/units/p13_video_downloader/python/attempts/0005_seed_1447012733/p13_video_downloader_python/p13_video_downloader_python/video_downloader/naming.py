"""Filename sanitation and uniqueness utilities."""

import os
import re
from typing import Set


def sanitize_filename(name: str) -> str:
    """Sanitize a filename by replacing invalid characters.

    Args:
        name: The raw filename string.

    Returns:
        A sanitized filename safe for use in filesystem operations.
    """
    if not isinstance(name, str):
        name = str(name)

    # Strip leading/trailing whitespace
    name = name.strip()

    # Replace runs of whitespace with underscore
    name = re.sub(r'\s+', '_', name)

    # Remove path separators and invalid characters
    # Keep only letters, digits, dots, dashes, and underscores
    name = re.sub(r'[^\w.-]', '', name)

    # Trim leading/trailing dots and underscores
    name = name.strip('. _')

    # Fallback to "download" if empty
    if not name:
        return "download"

    return name


def unique_name(base: str, existing: Set[str]) -> str:
    """Generate a unique filename by appending (1), (2), etc. if needed.

    Args:
        base: The base filename.
        existing: A set of existing filenames.

    Returns:
        A unique filename that is not in the existing set.
    """
    if base not in existing:
        return base

    # Split base into name and extension
    name, ext = os.path.splitext(base)
    
    # Try names with increasing numbers until we find an unused one
    counter = 1
    while True:
        new_name = f"{name} ({counter}){ext}"
        if new_name not in existing:
            return new_name
        counter += 1