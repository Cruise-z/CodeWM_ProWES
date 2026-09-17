"""Playlist ordering, current index, and navigation rules.

This module implements the Playlist class which manages an ordered collection
of Media items, tracks the currently selected item, and provides navigation
capabilities while enforcing bounds checking and preventing wrapping.
"""

from typing import List, Optional
from .media import Media
from .errors import NotFoundError


class Playlist:
    """Manages an ordered collection of Media items with navigation capabilities.

    The playlist maintains an internal list of Media items and tracks the
    currently selected item by index. Navigation methods respect playlist bounds
    and do not wrap around the playlist.
    """

    def __init__(self, items: List[Media]) -> None:
        """Initialize a new Playlist with the given list of Media items.

        Args:
            items: A list of Media objects to include in the playlist.
                   If empty, the playlist will have no current item.
        """
        self._items: List[Media] = list(items)
        if self._items:
            self._current_index: Optional[int] = 0
        else:
            self._current_index: Optional[int] = None

    def is_empty(self) -> bool:
        """Check if the playlist contains no items.

        Returns:
            True if the playlist is empty, False otherwise.
        """
        return len(self._items) == 0

    def size(self) -> int:
        """Get the number of items in the playlist.

        Returns:
            The count of Media items in the playlist.
        """
        return len(self._items)

    def current(self) -> Optional[Media]:
        """Get the currently selected Media item.

        Returns:
            The currently selected Media item, or None if the playlist is empty
            or no item is selected.
        """
        if self._current_index is None:
            return None
        return self._items[self._current_index]

    def select(self, index: int) -> Media:
        """Select and return the Media item at the specified index.

        Args:
            index: The zero-based index of the item to select.

        Returns:
            The Media item at the specified index.

        Raises:
            NotFoundError: If the index is out of bounds.
        """
        if index < 0 or index >= len(self._items):
            raise NotFoundError(f"Playlist index {index} out of range")
        self._current_index = index
        return self._items[index]

    def next(self) -> Optional[Media]:
        """Advance to and return the next Media item in the playlist.

        If the playlist is empty or currently at the last item, no change occurs
        and None is returned.

        Returns:
            The next Media item if available, otherwise None.
        """
        if self.is_empty():
            return None
        if self._current_index is None:
            # Should not happen if playlist is not empty, but defensive coding
            self._current_index = 0
            return self._items[0]
        
        if self._current_index >= len(self._items) - 1:
            # Already at the last item
            return None
        
        self._current_index += 1
        return self._items[self._current_index]

    def previous(self) -> Optional[Media]:
        """Go back to and return the previous Media item in the playlist.

        If the playlist is empty or currently at the first item, no change occurs
        and None is returned.

        Returns:
            The previous Media item if available, otherwise None.
        """
        if self.is_empty():
            return None
        if self._current_index is None:
            # Should not happen if playlist is not empty, but defensive coding
            self._current_index = 0
            return self._items[0]
        
        if self._current_index <= 0:
            # Already at the first item
            return None
        
        self._current_index -= 1
        return self._items[self._current_index]