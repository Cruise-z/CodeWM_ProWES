#include "Query.h"
#include <algorithm>
#include <set>
#include <string>
#include <vector>

namespace {
// Helper function to check if a tag is contained in a vector of tags
bool ContainsTag(const std::vector<std::string>& tags, const std::string& tag) {
  return std::find(tags.begin(), tags.end(), tag) != tags.end();
}
}  // namespace

FilterOptions Query::WithTags(const FilterOptions& options,
                              const std::vector<std::string>& tags) {
  FilterOptions new_options = options;
  // Normalize and add the new tags to the existing require_tags
  for (const auto& tag : tags) {
    std::string normalized_tag = Task::NormalizeTag(tag);
    if (!normalized_tag.empty()) {
      new_options.require_tags.push_back(normalized_tag);
    }
  }
  // Sort and remove duplicates from require_tags
  std::sort(new_options.require_tags.begin(), new_options.require_tags.end());
  new_options.require_tags.erase(
      std::unique(new_options.require_tags.begin(), new_options.require_tags.end()),
      new_options.require_tags.end());
  return new_options;
}

bool Query::matches(const Task& task, const FilterOptions& options) {
  // Check completion status
  if (options.completed.has_value()) {
    if (task.completed != options.completed.value()) {
      return false;
    }
  }

  // Check minimum priority
  if (options.min_priority.has_value()) {
    if (task.priority < options.min_priority.value()) {
      return false;
    }
  }

  // Check due date range
  if (options.due_before.has_value()) {
    int cmp = DateRules::compare_dates(task.due_date, options.due_before.value());
    if (cmp >= 0) {
      return false;
    }
  }

  if (options.due_after.has_value()) {
    int cmp = DateRules::compare_dates(task.due_date, options.due_after.value());
    if (cmp <= 0) {
      return false;
    }
  }

  // Check required tags
  if (!options.require_tags.empty()) {
    // Convert task tags to a set for faster lookup
    std::set<std::string> task_tags(task.tags.begin(), task.tags.end());
    
    // Check if all required tags are present
    for (const auto& required_tag : options.require_tags) {
      if (task_tags.find(required_tag) == task_tags.end()) {
        return false;
      }
    }
  }

  return true;
}

bool Query::less_due_priority(const Task& a, const Task& b) {
  // Compare due dates first
  int date_cmp = DateRules::compare_dates(a.due_date, b.due_date);
  if (date_cmp != 0) {
    return date_cmp < 0;
  }

  // If due dates are equal, compare priorities (higher priority comes first)
  if (a.priority != b.priority) {
    return a.priority > b.priority;
  }

  // If priorities are equal, compare titles
  if (a.title != b.title) {
    return a.title < b.title;
  }

  // If titles are equal, compare IDs
  return a.id < b.id;
}

bool Query::less_title(const Task& a, const Task& b) {
  // Compare titles first
  if (a.title != b.title) {
    return a.title < b.title;
  }

  // If titles are equal, compare IDs
  return a.id < b.id;
}