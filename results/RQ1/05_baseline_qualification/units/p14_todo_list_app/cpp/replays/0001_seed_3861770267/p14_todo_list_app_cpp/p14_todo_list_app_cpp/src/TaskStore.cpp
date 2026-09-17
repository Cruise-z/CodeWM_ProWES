#include "TaskStore.h"

bool InMemoryTaskStore::add(const Task& task) {
  if (tasks_.find(task.id) != tasks_.end()) {
    return false;
  }
  tasks_[task.id] = task;
  return true;
}

bool InMemoryTaskStore::update(const Task& task) {
  if (tasks_.find(task.id) == tasks_.end()) {
    return false;
  }
  tasks_[task.id] = task;
  return true;
}

bool InMemoryTaskStore::remove(std::uint64_t id) {
  auto it = tasks_.find(id);
  if (it == tasks_.end()) {
    return false;
  }
  tasks_.erase(it);
  return true;
}

Task* InMemoryTaskStore::find(std::uint64_t id) {
  auto it = tasks_.find(id);
  if (it == tasks_.end()) {
    return nullptr;
  }
  return &(it->second);
}

std::vector<Task> InMemoryTaskStore::get_all() const {
  std::vector<Task> result;
  result.reserve(tasks_.size());
  for (const auto& pair : tasks_) {
    result.push_back(pair.second);
  }
  return result;
}