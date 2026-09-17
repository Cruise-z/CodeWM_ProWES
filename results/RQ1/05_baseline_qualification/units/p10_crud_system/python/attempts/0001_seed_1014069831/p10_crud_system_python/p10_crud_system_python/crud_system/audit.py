"""Audit trail implementation for the CRUD system."""

from typing import List

from .types import AuditEvent


class AuditTrail:
    """An append-only in-memory audit trail for recording operations."""

    def __init__(self) -> None:
        """Initialize an empty audit trail."""
        self._events: List[AuditEvent] = []

    def log(self, op: str, item_id: int, item_name: str, ts: float) -> None:
        """Log an audit event with the given operation, item details, and timestamp.

        Args:
            op: The operation performed (e.g., "create", "update", "delete").
            item_id: The ID of the item involved in the operation.
            item_name: The name of the item involved in the operation.
            ts: The timestamp of the operation.
        """
        event = AuditEvent(op=op, item_id=item_id, item_name=item_name, ts=ts)
        self._events.append(event)

    def events(self) -> List[AuditEvent]:
        """Get all audit events.

        Returns:
            A list of all audit events recorded.
        """
        return self._events