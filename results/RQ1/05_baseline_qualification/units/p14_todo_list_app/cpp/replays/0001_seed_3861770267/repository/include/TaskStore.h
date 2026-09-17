#ifndef INCLUDE_TASKSTORE_H_
#define INCLUDE_TASKSTORE_H_

#include <cstdint>
#include <map>
#include <vector>
#include "Task.h"

/**
 * @brief Interface for task storage.
 */
class ITaskStore {
 public:
  virtual ~ITaskStore() = default;

  /**
   * @brief Adds a task to the store.
   * @param task The task to add.
   * @return True if the task was added successfully, false otherwise.
   */
  virtual bool add(const Task& task) = 0;

  /**
   * @brief Updates an existing task in the store.
   * @param task The task to update.
   * @return True if the task was updated successfully, false otherwise.
   */
  virtual bool update(const Task& task) = 0;

  /**
   * @brief Removes a task from the store by ID.
   * @param id The ID of the task to remove.
   * @return True if the task was removed successfully, false otherwise.
   */
  virtual bool remove(std::uint64_t id) = 0;

  /**
   * @brief Finds a task by ID.
   * @param id The ID of the task to find.
   * @return Pointer to the task if found, nullptr otherwise.
   */
  virtual Task* find(std::uint64_t id) = 0;

  /**
   * @brief Gets all tasks in the store.
   * @return A vector of all tasks, sorted by ID in ascending order.
   */
  virtual std::vector<Task> get_all() const = 0;
};

/**
 * @brief In-memory implementation of the task store.
 */
class InMemoryTaskStore : public ITaskStore {
 private:
  std::map<std::uint64_t, Task> tasks_;

 public:
  /**
   * @brief Adds a task to the store.
   * @param task The task to add.
   * @return True if the task was added successfully, false otherwise.
   */
  bool add(const Task& task) override;

  /**
   * @brief Updates an existing task in the store.
   * @param task The task to update.
   * @return True if the task was updated successfully, false otherwise.
   */
  bool update(const Task& task) override;

  /**
   * @brief Removes a task from the store by ID.
   * @param id The ID of the task to remove.
   * @return True if the task was removed successfully, false otherwise.
   */
  bool remove(std::uint64_t id) override;

  /**
   * @brief Finds a task by ID.
   * @param id The ID of the task to find.
   * @return Pointer to the task if found, nullptr otherwise.
   */
  Task* find(std::uint64_t id) override;

  /**
   * @brief Gets all tasks in the store.
   * @return A vector of all tasks, sorted by ID in ascending order.
   */
  std::vector<Task> get_all() const override;
};

#endif // INCLUDE_TASKSTORE_H_