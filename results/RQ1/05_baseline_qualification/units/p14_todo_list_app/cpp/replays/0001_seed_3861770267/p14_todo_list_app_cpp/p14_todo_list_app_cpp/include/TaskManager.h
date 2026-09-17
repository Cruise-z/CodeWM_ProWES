#ifndef INCLUDE_TASKMANAGER_H_
#define INCLUDE_TASKMANAGER_H_

#include <cstddef>
#include <cstdint>
#include <string>
#include <utility>
#include <vector>
#include "Query.h"
#include "TaskStore.h"

/**
 * @brief Manages tasks using an injected task store.
 */
class TaskManager {
 private:
  ITaskStore& store_;
  std::uint64_t next_id_;

 public:
  /**
   * @brief Constructs a TaskManager with the given task store.
   * @param store The task store to use.
   */
  explicit TaskManager(ITaskStore& store);

  /**
   * @brief Creates a new task.
   * @param title The title of the task.
   * @param description The description of the task.
   * @param due_date The due date of the task.
   * @param priority The priority of the task.
   * @param tags The tags associated with the task.
   * @return The ID of the created task.
   * @throws std::invalid_argument if the title or due date is invalid.
   */
  std::uint64_t create_task(const std::string& title,
                            const std::string& description,
                            const std::string& due_date,
                            Priority priority,
                            const std::vector<std::string>& tags);

  /**
   * @brief Edits an existing task.
   * @param id The ID of the task to edit.
   * @param title The new title of the task.
   * @param description The new description of the task.
   * @param due_date The new due date of the task.
   * @param priority The new priority of the task.
   * @param tags The new tags associated with the task.
   * @return True if the task was edited successfully, false if the task was not found.
   * @throws std::invalid_argument if the title or due date is invalid.
   */
  bool edit_task(std::uint64_t id,
                 const std::string& title,
                 const std::string& description,
                 const std::string& due_date,
                 Priority priority,
                 const std::vector<std::string>& tags);

  /**
   * @brief Deletes a task by ID.
   * @param id The ID of the task to delete.
   * @return True if the task was deleted successfully, false if the task was not found.
   */
  bool delete_task(std::uint64_t id);

  /**
   * @brief Sets the completion status of a task.
   * @param id The ID of the task.
   * @param completed The new completion status.
   * @return True if the task was updated successfully, false if the task was not found.
   */
  bool set_completed(std::uint64_t id, bool completed);

  /**
   * @brief Lists tasks based on filter options and sort order.
   * @param options The filter options to apply.
   * @param order The sort order to use.
   * @return A vector of tasks matching the criteria, sorted according to the order.
   */
  std::vector<Task> list(const FilterOptions& options, SortOrder order) const;

  /**
   * @brief Summarizes the tasks by counting completed and pending tasks.
   * @return A pair where the first element is the count of completed tasks and
   *         the second element is the count of pending tasks.
   */
  std::pair<std::size_t, std::size_t> summarize() const;
};

#endif // INCLUDE_TASKMANAGER_H_