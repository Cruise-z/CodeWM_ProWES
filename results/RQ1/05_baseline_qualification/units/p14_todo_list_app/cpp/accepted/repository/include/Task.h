#ifndef INCLUDE_TASK_H_
#define INCLUDE_TASK_H_

#include <cstdint>
#include <string>
#include <vector>

/**
 * @brief Priority levels for tasks.
 */
enum class Priority {
  Low,
  Medium,
  High
};

/**
 * @brief Represents a task in the to-do list application.
 */
struct Task {
  std::uint64_t id;
  std::string title;
  std::string description;
  std::string due_date;
  Priority priority;
  std::vector<std::string> tags;
  bool completed;

  /**
   * @brief Trims whitespace from the beginning and end of a string.
   * @param str The input string to trim.
   * @return The trimmed string.
   */
  static std::string Trim(const std::string& str);

  /**
   * @brief Normalizes a single tag by trimming and converting to lowercase.
   * @param tag The input tag to normalize.
   * @return The normalized tag.
   */
  static std::string NormalizeTag(const std::string& tag);

  /**
   * @brief Normalizes a vector of tags by trimming, lowercasing, removing
   *        empty tags, sorting, and deduplicating them deterministically.
   * @param tags The input vector of tags to normalize.
   * @return The normalized vector of tags.
   */
  static std::vector<std::string> NormalizeTags(const std::vector<std::string>& tags);

  /**
   * @brief Checks if a title is valid (not empty).
   * @param title The title to validate.
   * @return True if the title is valid, false otherwise.
   */
  static bool IsValidTitle(const std::string& title);
};

#endif // INCLUDE_TASK_H_