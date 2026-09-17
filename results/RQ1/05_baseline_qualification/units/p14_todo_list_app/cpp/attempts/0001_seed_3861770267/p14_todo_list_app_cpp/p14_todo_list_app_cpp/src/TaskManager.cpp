#include "TaskManager.h"
#include <algorithm>
#include <stdexcept>

TaskManager::TaskManager(ITaskStore& store) : store_(store), next_id_(1) {}

std::uint64_t TaskManager::create_task(const std::string& title,
                                       const std::string& description,
                                       const std::string& due_date,
                                       Priority priority,
                                       const std::vector<std::string>& tags) {
  // Validate title
  if (!Task::IsValidTitle(title)) {
    throw std::invalid_argument("Invalid title: title cannot be empty");
  }

  // Validate due date if provided
  if (!due_date.empty() && !DateRules::is_valid_iso_date(due_date)) {
    throw std::invalid_argument("Invalid due date: must be in YYYY-MM-DD format");
  }

  // Normalize tags
  auto normalized_tags = Task::NormalizeTags(tags);

  // Create task
  Task task;
  task.id = next_id_++;
  task.title = title;
  task.description = description;
  task.due_date = due_date;
  task.priority = priority;
  task.tags = normalized_tags;
  task.completed = false;

  // Add to store
  if (!store_.add(task)) {
    // This shouldn't happen with a fresh ID, but handle gracefully
    throw std::runtime_error("Failed to add task to store");
  }

  return task.id;
}

bool TaskManager::edit_task(std::uint64_t id,
                            const std::string& title,
                            const std::string& description,
                            const std::string& due_date,
                            Priority priority,
                            const std::vector<std::string>& tags) {
  // Find the task
  Task* task_ptr = store_.find(id);
  if (task_ptr == nullptr) {
    return false;
  }

  Task& task = *task_ptr;

  // Validate title
  if (!Task::IsValidTitle(title)) {
    throw std::invalid_argument("Invalid title: title cannot be empty");
  }

  // Validate due date if provided
  if (!due_date.empty() && !DateRules::is_valid_iso_date(due_date)) {
    throw std::invalid_argument("Invalid due date: must be in YYYY-MM-DD format");
  }

  // Update task fields
  task.title = title;
  task.description = description;
  task.due_date = due_date;
  task.priority = priority;
  task.tags = Task::NormalizeTags(tags);

  // Update in store
  return store_.update(task);
}

bool TaskManager::delete_task(std::uint64_t id) {
  return store_.remove(id);
}

bool TaskManager::set_completed(std::uint64_t id, bool completed) {
  Task* task_ptr = store_.find(id);
  if (task_ptr == nullptr) {
    return false;
  }

  task_ptr->completed = completed;
  return store_.update(*task_ptr);
}

std::vector<Task> TaskManager::list(const FilterOptions& options, SortOrder order) const {
  // Get all tasks
  auto all_tasks = store_.get_all();

  // Filter tasks
  std::vector<Task> filtered_tasks;
  std::copy_if(all_tasks.begin(), all_tasks.end(), std::back_inserter(filtered_tasks),
               [&options](const Task& task) {
                 return Query::matches(task, options);
               });

  // Sort tasks
  if (order == SortOrder::ByDueThenPriority) {
    std::sort(filtered_tasks.begin(), filtered_tasks.end(), Query::less_due_priority);
  } else {
    std::sort(filtered_tasks.begin(), filtered_tasks.end(), Query::less_title);
  }

  return filtered_tasks;
}

std::pair<std::size_t, std::size_t> TaskManager::summarize() const {
  auto all_tasks = store_.get_all();
  
  std::size_t completed_count = 0;
  std::size_t pending_count = 0;
  
  for (const auto& task : all_tasks) {
    if (task.completed) {
      completed_count++;
    } else {
      pending_count++;
    }
  }
  
  return std::make_pair(completed_count, pending_count);
}