"""Filename sanitation and unique naming utilities for video downloader."""

import re
from pathlib import PurePosixPath
from typing import Set


def sanitize_filename(name: str) -> str:
    """
    Sanitize a filename by replacing invalid characters.

    Args:
        name: The raw filename string.

    Returns:
        A sanitized filename string safe for use in filesystem operations.
    """
    if not isinstance(name, str):
        name = str(name)

    # Strip leading/trailing whitespace
    name = name.strip()

    # Replace runs of whitespace with underscores
    name = re.sub(r"\s+", "_", name)

    # Remove path separators and invalid characters
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)

    # Trim leading/trailing dots and underscores
    name = name.strip("._")

    # Return fallback if empty
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
        base = str(base)

    if base not in existing:
        return base

    path = PurePosixPath(base)
    stem = path.stem
    suffix = path.suffix

    # Sanitize the stem for uniqueness check
    sanitized_stem = sanitize_filename(stem)

    counter = 1
    while True:
        new_name = f"{sanitized_stem} ({counter}){suffix}"
        if new_name not in existing:
            return new_name
        counter += 1