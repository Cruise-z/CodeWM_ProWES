"""Runtime demonstration of the CRUD system with deterministic timestamps."""

from crud_system import (
    Repository,
    FixedClock,
    AuditTrail,
    Service
)


def main():
    """Run a bounded, non-interactive demonstration of the CRUD system."""
    # Create components as specified in the protocol
    repo = Repository()
    clock = FixedClock(base=100.0, step=10.0)
    audit = AuditTrail()
    service = Service(repo, audit, clock)
    
    # Perform operations as described in the test cases
    # Create an item
    item1 = service.create("Alpha")
    
    # Update the item
    item2 = service.update(item1.id, "Alpha2")
    
    # Search for items (should return all items sorted by name)
    page = service.search(limit=2, offset=0)
    
    # Delete the item
    service.delete(item2.id)
    
    # Print results to demonstrate successful execution
    print("CRUD demonstration completed successfully.")
    print(f"Created item: {item1}")
    print(f"Updated item: {item2}")
    print(f"Search result page: {page}")
    print(f"Audit events: {service.audit_events()}")


if __name__ == "__main__":
    main()