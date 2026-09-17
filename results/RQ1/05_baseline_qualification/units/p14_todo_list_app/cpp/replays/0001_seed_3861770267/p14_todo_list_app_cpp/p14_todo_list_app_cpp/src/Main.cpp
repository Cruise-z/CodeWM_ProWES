#include "TaskManager.h"
#include "TaskStore.h"
#include <iostream>

int main() {
  // Create an in-memory task store
  InMemoryTaskStore store;
  
  // Create a task manager with the store
  TaskManager manager(store);
  
  // Create a few tasks
  auto task1_id = manager.create_task("Buy groceries", "Buy milk, bread, and eggs", "2023-12-01", Priority::High, {"shopping", "home"});
  auto task2_id = manager.create_task("Read book", "Finish reading 'C++ Primer'", "2023-12-15", Priority::Medium, {"reading", "learning"});
  auto task3_id = manager.create_task("Call mom", "Check in with mom about her health", "", Priority::Low, {"personal"});
  
  // List all tasks sorted by due date and priority
  FilterOptions options;
  auto tasks = manager.list(options, SortOrder::ByDueThenPriority);
  
  std::cout << "All tasks:" << std::endl;
  for (const auto& task : tasks) {
    std::cout << "ID: " << task.id 
              << ", Title: " << task.title 
              << ", Due: " << task.due_date 
              << ", Priority: " << static_cast<int>(task.priority)
              << ", Tags: ";
    for (size_t i = 0; i < task.tags.size(); ++i) {
      std::cout << task.tags[i];
      if (i < task.tags.size() - 1) {
        std::cout << ", ";
      }
    }
    std::cout << ", Completed: " << (task.completed ? "Yes" : "No") << std::endl;
  }
  
  // Summarize tasks
  auto [completed, pending] = manager.summarize();
  std::cout << "\nSummary:" << std::endl;
  std::cout << "Completed: " << completed << std::endl;
  std::cout << "Pending: " << pending << std::endl;
  
  return 0;
}