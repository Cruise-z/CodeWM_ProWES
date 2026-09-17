"""Pagination functionality for the CRUD system."""

from typing import List, Optional

from .errors import PaginationError
from .types import Item, Page


def paginate(items: List[Item], limit: Optional[int] = None, offset: int = 0) -> Page:
    """Paginate a list of items according to the given limit and offset.

    Args:
        items: The list of items to paginate.
        limit: The maximum number of items to return. If None, all items are returned.
        offset: The starting index of the items to return.

    Returns:
        A Page object containing the paginated items and metadata.

    Raises:
        PaginationError: If offset is negative or limit is negative and not None.
    """
    if offset < 0:
        raise PaginationError("Offset cannot be negative")
    
    if limit is not None and limit < 0:
        raise PaginationError("Limit cannot be negative")
    
    total = len(items)
    effective_limit = limit if limit is not None else total
    
    # Ensure we don't go beyond the total number of items
    start_index = offset
    end_index = min(offset + effective_limit, total)
    
    selected = items[start_index:end_index]
    
    return Page(
        items=selected,
        total=total,
        limit=effective_limit,
        offset=offset
    )