"""In-memory repository implementation for the CRUD system."""

from typing import List, Optional
from .errors import DuplicateNameError, NotFoundError
from .types import Item


class Repository:
    """In-memory repository with stable IDs and name uniqueness enforcement."""

    def __init__(self) -> None:
        """Initialize an empty repository."""
        self._items: dict[int, Item] = {}
        self._name_index: dict[str, int] = {}
        self._next_id: int = 1

    def create(self, name: str, ts: float) -> Item:
        """Create a new item with the given name and timestamp.

        Args:
            name: The name of the item to create.
            ts: The timestamp for the item's creation and update.

        Returns:
            The newly created Item.

        Raises:
            DuplicateNameError: If an item with the given name already exists.
        """
        if self.exists_name(name):
            raise DuplicateNameError(f"Item with name '{name}' already exists")

        item = Item(
            id=self._next_id,
            name=name,
            created_at=ts,
            updated_at=ts
        )
        self._items[item.id] = item
        self._name_index[name] = item.id
        self._next_id += 1
        return item

    def get(self, item_id: int) -> Item:
        """Retrieve an item by its ID.

        Args:
            item_id: The ID of the item to retrieve.

        Returns:
            The requested Item.

        Raises:
            NotFoundError: If no item with the given ID exists.
        """
        if item_id not in self._items:
            raise NotFoundError(f"Item with id {item_id} not found")
        return self._items[item_id]

    def update(self, item_id: int, name: str, ts: float) -> Item:
        """Update an existing item's name and timestamp.

        Args:
            item_id: The ID of the item to update.
            name: The new name for the item.
            ts: The timestamp for the update.

        Returns:
            The updated Item.

        Raises:
            NotFoundError: If no item with the given ID exists.
            DuplicateNameError: If another item has the given name.
        """
        if item_id not in self._items:
            raise NotFoundError(f"Item with id {item_id} not found")

        old_item = self._items[item_id]
        if old_item.name != name and self.exists_name(name):
            raise DuplicateNameError(f"Item with name '{name}' already exists")

        # Remove old name from index if it was different
        if old_item.name != name:
            del self._name_index[old_item.name]

        # Update the item
        updated_item = Item(
            id=item_id,
            name=name,
            created_at=old_item.created_at,
            updated_at=ts
        )
        self._items[item_id] = updated_item
        self._name_index[name] = item_id
        return updated_item

    def delete(self, item_id: int) -> None:
        """Delete an item by its ID.

        Args:
            item_id: The ID of the item to delete.

        Raises:
            NotFoundError: If no item with the given ID exists.
        """
        if item_id not in self._items:
            raise NotFoundError(f"Item with id {item_id} not found")

        item = self._items[item_id]
        del self._name_index[item.name]
        del self._items[item_id]

    def list_items(self) -> List[Item]:
        """List all items sorted by name.

        Returns:
            A list of all items sorted by their names.
        """
        return sorted(self._items.values(), key=lambda x: x.name)

    def exists_name(self, name: str) -> bool:
        """Check if an item with the given name exists.

        Args:
            name: The name to check.

        Returns:
            True if an item with the name exists, False otherwise.
        """
        return name in self._name_index