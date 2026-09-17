"""Filename sanitation and unique naming utilities."""

import re
import os
from typing import Set


def sanitize_filename(name: str) -> str:
    """
    Sanitize a filename by removing invalid characters and normalizing whitespace.

    Args:
        name: The raw filename string to sanitize.

    Returns:
        A sanitized filename string.
    """
    if not isinstance(name, str):
        name = str(name)
    
    # Strip leading/trailing whitespace
    name = name.strip()
    
    # Replace sequences of whitespace with underscores
    name = re.sub(r'\s+', '_', name)
    
    # Remove path separators and invalid characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    
    # Trim leading/trailing dots and underscores
    name = name.strip('. _')
    
    # Fall back to "download" if the result is empty or all invalid chars
    if not name:
        return "download"
    
    return name


def unique_name(base: str, existing: Set[str]) -> str:
    """
    Generate a unique filename by appending (1), (2), etc. if necessary.

    Args:
        base: The base filename.
        existing: A set of existing filenames.

    Returns:
        A unique filename that is not in the existing set.
    """
    if base not in existing:
        return base
    
    # Split the base into name and extension
    name, ext = os.path.splitext(base)
    
    # Try increasing numbers until we find an unused name
    i = 1
    while True:
        new_name = f"{name} ({i}){ext}"
        if new_name not in existing:
            return new_name
        i += 1