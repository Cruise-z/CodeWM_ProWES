#include "Repository.h"

bool Repository::insert(const Record& record) {
  auto [_, inserted] = records_.insert({record.id, record});
  return inserted;
}

std::optional<Record> Repository::find(const std::string& id) const {
  auto it = records_.find(id);
  if (it != records_.end()) {
    return it->second;
  }
  return std::nullopt;
}

bool Repository::replace(const Record& record) {
  auto it = records_.find(record.id);
  if (it == records_.end()) {
    return false;
  }
  it->second = record;
  return true;
}

bool Repository::erase(const std::string& id) {
  return records_.erase(id) > 0;
}

std::vector<Record> Repository::list() const {
  std::vector<Record> result;
  result.reserve(records_.size());
  for (const auto& pair : records_) {
    result.push_back(pair.second);
  }
  return result;
}