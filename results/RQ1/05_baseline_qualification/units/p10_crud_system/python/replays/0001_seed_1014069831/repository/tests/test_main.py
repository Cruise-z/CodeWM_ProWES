"""Tests for the CRUD system demonstrating deterministic behavior."""

import pytest
from crud_system import (
    Repository,
    FixedClock,
    AuditTrail,
    Service,
    ValidationError,
    DuplicateNameError,
    NotFoundError,
    PaginationError
)


def test_crud_timestamps():
    """Test that CRUD operations use the correct timestamps from FixedClock."""
    # Setup components as specified in the protocol
    repo = Repository()
    clock = FixedClock(base=100.0, step=10.0)
    audit = AuditTrail()
    service = Service(repo, audit, clock)
    
    # Create an item - should be timestamped at 100.0
    item1 = service.create("Alpha")
    assert item1.created_at == 100.0
    assert item1.updated_at == 100.0
    
    # Verify audit event was logged with same timestamp
    audit_events = service.audit_events()
    assert len(audit_events) == 1
    assert audit_events[0].op == "create"
    assert audit_events[0].ts == 100.0
    assert audit_events[0].item_name == "Alpha"
    
    # Update the item - should be timestamped at 110.0
    item2 = service.update(item1.id, "Alpha2")
    assert item2.updated_at == 110.0
    
    # Verify audit event was logged with same timestamp
    audit_events = service.audit_events()
    assert len(audit_events) == 2
    assert audit_events[1].op == "update"
    assert audit_events[1].ts == 110.0
    assert audit_events[1].item_name == "Alpha2"


def test_duplicate_and_not_found_errors():
    """Test that duplicate name creation raises DuplicateNameError 
    and missing item access raises NotFoundError.
    """
    # Setup components as specified in the protocol
    repo = Repository()
    clock = FixedClock(base=100.0, step=10.0)
    audit = AuditTrail()
    service = Service(repo, audit, clock)
    
    # Create an item
    service.create("Alpha")
    
    # Try to create another item with the same name - should raise DuplicateNameError
    with pytest.raises(DuplicateNameError):
        service.create("Alpha")
    
    # Try to update a non-existent item - should raise NotFoundError
    with pytest.raises(NotFoundError):
        service.update(999, "NonExistent")
    
    # Try to delete a non-existent item - should raise NotFoundError
    with pytest.raises(NotFoundError):
        service.delete(999)


def test_pagination_and_audit_timing():
    """Test pagination with Alpha, Beta, Gamma items and verify audit timestamps."""
    # Setup components as specified in the protocol
    repo = Repository()
    clock = FixedClock(base=100.0, step=10.0)
    audit = AuditTrail()
    service = Service(repo, audit, clock)
    
    # Create items in order: Alpha, Beta, Gamma
    service.create("Alpha")
    service.create("Beta")
    service.create("Gamma")
    
    # Test pagination with limit=2, offset=1
    # Should return items with names "Beta" and "Gamma"
    page = service.search(limit=2, offset=1)
    
    # Verify pagination results
    assert page.total == 3
    assert page.limit == 2
    assert page.offset == 1
    assert len(page.items) == 2
    assert page.items[0].name == "Beta"
    assert page.items[1].name == "Gamma"
    
    # Verify audit timestamps are exactly [100.0, 110.0, 120.0]
    audit_events = service.audit_events()
    assert len(audit_events) == 3
    assert [event.ts for event in audit_events] == [100.0, 110.0, 120.0]