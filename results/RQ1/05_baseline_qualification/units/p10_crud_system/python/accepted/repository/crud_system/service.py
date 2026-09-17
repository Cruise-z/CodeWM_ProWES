"""Service layer for the CRUD system orchestrating repository, audit, and clock operations."""

from typing import List, Optional

from .clock import FixedClock
from .repository import Repository
from .audit import AuditTrail
from .types import Item, Page
from .validation import validate_name


class Service:
    """Service layer that orchestrates CRUD operations, search, and audit logging."""

    def __init__(
        self,
        repo: Repository,
        audit: AuditTrail,
        clock: FixedClock
    ) -> None:
        """Initialize the service with repository, audit trail, and clock.

        Args:
            repo: The repository instance to use for data storage.
            audit: The audit trail instance to record operations.
            clock: The clock instance to provide timestamps.
        """
        self._repo = repo
        self._audit = audit
        self._clock = clock

    def create(self, name: str) -> Item:
        """Create a new item with the given name.

        Args:
            name: The name of the item to create.

        Returns:
            The newly created Item.

        Raises:
            ValidationError: If the name is invalid.
        """
        validate_name(name)
        ts = self._clock.now()
        item = self._repo.create(name, ts)
        self._audit.log("create", item.id, item.name, ts)
        return item

    def read(self, item_id: int) -> Item:
        """Retrieve an item by its ID.

        Args:
            item_id: The ID of the item to retrieve.

        Returns:
            The requested Item.

        Raises:
            NotFoundError: If no item with the given ID exists.
        """
        return self._repo.get(item_id)

    def update(self, item_id: int, name: str) -> Item:
        """Update an existing item's name.

        Args:
            item_id: The ID of the item to update.
            name: The new name for the item.

        Returns:
            The updated Item.

        Raises:
            NotFoundError: If no item with the given ID exists.
            ValidationError: If the name is invalid.
            DuplicateNameError: If another item has the given name.
        """
        validate_name(name)
        ts = self._clock.now()
        item = self._repo.update(item_id, name, ts)
        self._audit.log("update", item.id, item.name, ts)
        return item

    def delete(self, item_id: int) -> None:
        """Delete an item by its ID.

        Args:
            item_id: The ID of the item to delete.

        Raises:
            NotFoundError: If no item with the given ID exists.
        """
        item = self._repo.get(item_id)
        ts = self._clock.now()
        self._repo.delete(item_id)
        self._audit.log("delete", item.id, item.name, ts)

    def search(
        self,
        name_contains: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> Page:
        """Search for items with optional name filtering and pagination.

        Args:
            name_contains: If provided, only items whose names contain this substring will be returned.
            limit: Maximum number of items to return. If None, all matching items are returned.
            offset: Starting index for pagination.

        Returns:
            A Page object containing the matching items and pagination metadata.
        """
        items = self._repo.list_items()
        
        if name_contains is not None:
            items = [item for item in items if name_contains in item.name]
            
        return self._paginate(items, limit, offset)

    def audit_events(self) -> List[Item]:
        """Get all audit events.

        Returns:
            A list of all audit events recorded.
        """
        return self._audit.events()

    def _paginate(self, items: List[Item], limit: Optional[int], offset: int) -> Page:
        """Helper method to paginate items.

        Args:
            items: The list of items to paginate.
            limit: Maximum number of items to return.
            offset: Starting index for pagination.

        Returns:
            A Page object with paginated results.
        """
        from .search import paginate
        return paginate(items, limit, offset)