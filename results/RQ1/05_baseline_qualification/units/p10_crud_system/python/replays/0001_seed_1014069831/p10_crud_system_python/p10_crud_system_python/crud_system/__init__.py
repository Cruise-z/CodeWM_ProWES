"""Canonical API exports for the CRUD system."""

from .errors import (
    ValidationError,
    DuplicateNameError,
    NotFoundError,
    PaginationError
)
from .types import (
    Item,
    AuditEvent,
    Page
)
from .clock import FixedClock
from .repository import Repository
from .audit import AuditTrail
from .service import Service
from .search import paginate

__all__ = [
    "Item",
    "AuditEvent",
    "Page",
    "FixedClock",
    "Repository",
    "AuditTrail",
    "Service",
    "paginate",
    "ValidationError",
    "DuplicateNameError",
    "NotFoundError",
    "PaginationError"
]