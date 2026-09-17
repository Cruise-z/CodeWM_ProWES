#include <cassert>
#include <stdexcept>
#include <string>
#include "CrudService.h"

int main() {
  // Block 1: CRUD lifecycle at times 100/105
  {
    Repository repo;
    ManualClock clock(100);
    CrudService service(repo, clock);
    
    // Create record
    Record created = service.create("1", "Alice", "alice@example.com");
    assert(created.revision == 1);
    assert(created.updated_at == 100);
    
    // Get record
    auto found = service.get("1");
    assert(found.has_value());
    assert(found->id == "1");
    assert(found->name == "Alice");
    assert(found->email == "alice@example.com");
    assert(found->revision == 1);
    assert(found->updated_at == 100);
    
    // Advance time
    clock.advance(5);
    
    // Update record
    Record updated = service.update("1", "Alice Smith", "alice@example.com");
    assert(updated.revision == 2);
    assert(updated.updated_at == 105);
    
    // Remove record
    assert(service.remove("1") == true);
    
    // Verify removal
    assert(!service.get("1").has_value());
  }
  
  // Block 2: Invalid inputs and duplicate handling
  {
    Repository repo;
    ManualClock clock(100);
    CrudService service(repo, clock);
    
    // Blank name
    try {
      service.create("2", "", "test@example.com");
      assert(false); // Should not reach here
    } catch (const std::invalid_argument&) {
      // Expected
    }
    
    // Malformed email (no @)
    try {
      service.create("3", "Bob", "invalid-email");
      assert(false); // Should not reach here
    } catch (const std::invalid_argument&) {
      // Expected
    }
    
    // Malformed email (@ at beginning)
    try {
      service.create("4", "Charlie", "@example.com");
      assert(false); // Should not reach here
    } catch (const std::invalid_argument&) {
      // Expected
    }
    
    // Malformed email (@ at end)
    try {
      service.create("5", "David", "example@");
      assert(false); // Should not reach here
    } catch (const std::invalid_argument&) {
      // Expected
    }
    
    // Malformed email (multiple @)
    try {
      service.create("6", "Eve", "test@@example.com");
      assert(false); // Should not reach here
    } catch (const std::invalid_argument&) {
      // Expected
    }
    
    // Duplicate ID
    service.create("7", "Frank", "frank@example.com");
    try {
      service.create("7", "George", "george@example.com");
      assert(false); // Should not reach here
    } catch (const std::runtime_error&) {
      // Expected
    }
  }
  
  // Block 3: Deterministic list order
  {
    Repository repo;
    ManualClock clock(100);
    CrudService service(repo, clock);
    
    // Create records in reverse order
    service.create("b", "Bob", "bob@example.com");
    service.create("a", "Alice", "alice@example.com");
    
    // List records
    auto records = service.list();
    assert(records.size() == 2);
    assert(records[0].id == "a");
    assert(records[1].id == "b");
  }
  
  return 0;
}