"""Data structures for the CRUD system."""

from dataclasses import dataclass
from typing import List


@dataclass
class Item:
    """Represents an item with a stable identifier and timestamps."""

    id: int
    name: str
    created_at: float
    updated_at: float


@dataclass
class AuditEvent:
    """Represents an audit event with operation, item details, and timestamp."""

    op: str
    item_id: int
    item_name: str
    ts: float


@dataclass
class Page:
    """Represents a paginated result set with items and metadata."""

    items: List[Item]
    total: int
    limit: int
    offset: int