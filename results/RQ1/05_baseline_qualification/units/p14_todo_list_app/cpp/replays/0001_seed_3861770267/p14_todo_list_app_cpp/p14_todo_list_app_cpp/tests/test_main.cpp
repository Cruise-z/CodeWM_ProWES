#include <cassert>
#include <stdexcept>
#include <vector>
#include "TaskManager.h"

int main() {
  // Block 1: Basic wiring - create two local tasks, list with global SortOrder::ByDueThenPriority,
  // and verify deterministic order plus summarize completed/pending counts
  {
    InMemoryTaskStore store;
    TaskManager manager(store);
    
    // Create two tasks
    const auto task1_id = manager.create_task("Task 1", "Description 1", "2023-12-01", Priority::High, {"tag1"});
    const auto task2_id = manager.create_task("Task 2", "Description 2", "2023-11-01", Priority::Medium, {"tag2"});
    
    // List tasks sorted by due date and priority
    FilterOptions options;
    const auto tasks = manager.list(options, SortOrder::ByDueThenPriority);
    
    // Verify deterministic order (earlier date first)
    assert(tasks.size() == 2);
    assert(tasks[0].id == task2_id);  // Earlier due date
    assert(tasks[1].id == task1_id);  // Later due date
    
    // Summarize tasks
    const auto [completed, pending] = manager.summarize();
    assert(completed == 0);
    assert(pending == 2);
  }
  
  // Block 2: Invalid data with fresh local store/manager
  {
    InMemoryTaskStore store;
    TaskManager manager(store);
    
    // First create a valid task to get an existing ID
    const auto existing_id = manager.create_task("Existing", "", "", Priority::Low, {});
    
    // create_task rejects blank title
    try {
      manager.create_task("", "desc", "", Priority::Low, {});
      assert(false);  // Should not reach here
    } catch (const std::invalid_argument&) {
      // Expected
    }
    
    // create_task rejects invalid date
    try {
      manager.create_task("Valid", "desc", "invalid-date", Priority::Low, {});
      assert(false);  // Should not reach here
    } catch (const std::invalid_argument&) {
      // Expected
    }
    
    // edit_task on a missing arbitrary id returns false
    assert(!manager.edit_task(999, "New Title", "", "", Priority::Low, {}));
    
    // edit_task with existing_id and blank title throws invalid_argument
    try {
      manager.edit_task(existing_id, "", "new desc", "", Priority::High, {});
      assert(false);  // Should not reach here
    } catch (const std::invalid_argument&) {
      // Expected
    }
  }
  
  // Block 3: Normalized tags and ordering with fresh local store/manager
  {
    InMemoryTaskStore store;
    TaskManager manager(store);
    
    // Create tasks with various tag formats
    const auto task1_id = manager.create_task("Task 1", "", "2023-12-01", Priority::High, {"  TagA  ", "tagB", "TAGA"});
    const auto task2_id = manager.create_task("Task 2", "", "2023-11-01", Priority::Medium, {"tagC", "  tagB  "});
    
    // Test that tags are normalized (lowercase, trimmed, deduplicated)
    FilterOptions options;
    const auto tasks = manager.list(options, SortOrder::ByDueThenPriority);
    
    // Verify the first task's tags are normalized
    const std::vector<std::string> expected_tags1{"taga", "tagb"};
    assert(tasks[0].tags == expected_tags1);
    
    // Verify the second task's tags are normalized
    const std::vector<std::string> expected_tags2{"tagb", "tagc"};
    assert(tasks[1].tags == expected_tags2);
    
    // Test due date ordering: valid dates sort before empty dates
    const auto task3_id = manager.create_task("Task 3", "", "", Priority::Low, {});  // Empty due date
    
    // Re-list to verify ordering
    const auto tasks_sorted_by_date = manager.list(options, SortOrder::ByDueThenPriority);
    
    // Task with valid date should come first
    assert(tasks_sorted_by_date[0].id == task2_id);
    assert(tasks_sorted_by_date[1].id == task1_id);
    assert(tasks_sorted_by_date[2].id == task3_id);
    
    // Test title ordering
    const auto tasks_sorted_by_title = manager.list(options, SortOrder::ByTitle);
    assert(tasks_sorted_by_title[0].id == task1_id);
    assert(tasks_sorted_by_title[1].id == task2_id);
    assert(tasks_sorted_by_title[2].id == task3_id);
  }
  
  return 0;
}