#ifndef INCLUDE_QUERY_H_
#define INCLUDE_QUERY_H_

#include <optional>
#include <string>
#include <vector>
#include "Date.h"
#include "Task.h"

/**
 * @brief Sorting order for tasks.
 */
enum class SortOrder {
  ByDueThenPriority,
  ByTitle
};

/**
 * @brief Options for filtering tasks.
 */
struct FilterOptions {
  std::optional<bool> completed;
  std::optional<Priority> min_priority;
  std::optional<std::string> due_before;
  std::optional<std::string> due_after;
  std::vector<std::string> require_tags;
};

/**
 * @brief Provides query operations for filtering and sorting tasks.
 */
class Query {
 public:
  /**
   * @brief Creates a new FilterOptions with additional required tags.
   * @param options The base filter options.
   * @param tags The tags to add as requirements.
   * @return A new FilterOptions with the additional tags.
   */
  static FilterOptions WithTags(const FilterOptions& options,
                                const std::vector<std::string>& tags);

  /**
   * @brief Checks if a task matches the given filter options.
   * @param task The task to check.
   * @param options The filter options to apply.
   * @return True if the task matches all filters, false otherwise.
   */
  static bool matches(const Task& task, const FilterOptions& options);

  /**
   * @brief Compares two tasks for sorting by due date and priority.
   * @param a First task.
   * @param b Second task.
   * @return True if a should come before b in the sorted list.
   */
  static bool less_due_priority(const Task& a, const Task& b);

  /**
   * @brief Compares two tasks for sorting by title.
   * @param a First task.
   * @param b Second task.
   * @return True if a should come before b in the sorted list.
   */
  static bool less_title(const Task& a, const Task& b);
};

#endif // INCLUDE_QUERY_H_