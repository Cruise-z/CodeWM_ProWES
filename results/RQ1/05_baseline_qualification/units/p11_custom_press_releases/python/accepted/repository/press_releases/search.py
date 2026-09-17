"""Search utilities for press releases."""

from typing import List, Optional

from .press_release import PressRelease


def search_by_tag(releases: List[Optional[PressRelease]], tag: str) -> List[PressRelease]:
    """Search for press releases by tag.

    Args:
        releases: List of press releases to search through.
        tag: The tag to search for (case-insensitive, trimmed).

    Returns:
        A list of press releases that have the specified tag.
        Order is preserved, None entries are ignored.
    """
    normalized_tag = tag.strip().lower()
    result = []
    for release in releases:
        if release is None:
            continue
        tags = release.tags()
        if any(normalized_tag == t.lower() for t in tags):
            result.append(release)
    return result


def search_text(releases: List[Optional[PressRelease]], query: str) -> List[PressRelease]:
    """Search for press releases by text content.

    Args:
        releases: List of press releases to search through.
        query: The text to search for (case-insensitive).

    Returns:
        A list of press releases whose headline or body contains the query.
        Order is preserved, None entries are ignored.
    """
    normalized_query = query.strip().lower()
    result = []
    for release in releases:
        if release is None:
            continue
        headline = release.headline
        body = release.body
        if normalized_query in headline.lower() or normalized_query in body.lower():
            result.append(release)
    return result