#include "CrudService.h"
#include <stdexcept>
#include <algorithm>

CrudService::CrudService(Repository& repository, ManualClock& clock)
    : repository_(repository), clock_(clock) {}

Record CrudService::create(const std::string& id, const std::string& name, const std::string& email) {
  // Validate inputs
  if (id.empty()) {
    throw std::invalid_argument("ID cannot be blank");
  }
  if (name.empty()) {
    throw std::invalid_argument("Name cannot be blank");
  }
  
  // Validate email format: exactly one '@' not at edges
  size_t at_pos = email.find('@');
  if (at_pos == std::string::npos || at_pos == 0 || at_pos == email.length() - 1) {
    throw std::invalid_argument("Email must contain exactly one '@' not at edges");
  }
  // Check for second '@'
  if (email.find('@', at_pos + 1) != std::string::npos) {
    throw std::invalid_argument("Email must contain exactly one '@' not at edges");
  }

  // Check for duplicate ID
  if (repository_.find(id)) {
    throw std::runtime_error("Record with ID already exists");
  }

  std::uint64_t timestamp = clock_.now();
  Record record(id, name, email, 1, timestamp);
  if (repository_.insert(record)) {
    return record;
  }
  
  // This should never happen due to the duplicate check above
  throw std::runtime_error("Failed to insert record");
}

std::optional<Record> CrudService::get(const std::string& id) const {
  return repository_.find(id);
}

Record CrudService::update(const std::string& id, const std::string& name, const std::string& email) {
  // Validate inputs
  if (id.empty()) {
    throw std::invalid_argument("ID cannot be blank");
  }
  if (name.empty()) {
    throw std::invalid_argument("Name cannot be blank");
  }
  
  // Validate email format: exactly one '@' not at edges
  size_t at_pos = email.find('@');
  if (at_pos == std::string::npos || at_pos == 0 || at_pos == email.length() - 1) {
    throw std::invalid_argument("Email must contain exactly one '@' not at edges");
  }
  // Check for second '@'
  if (email.find('@', at_pos + 1) != std::string::npos) {
    throw std::invalid_argument("Email must contain exactly one '@' not at edges");
  }

  // Find existing record
  auto existing = repository_.find(id);
  if (!existing) {
    throw std::runtime_error("Record with ID does not exist");
  }

  // Update fields while preserving ID and incrementing revision
  std::uint64_t timestamp = clock_.now();
  Record updated_record(id, name, email, existing->revision + 1, timestamp);
  
  if (repository_.replace(updated_record)) {
    return updated_record;
  }
  
  // This should never happen due to the existence check above
  throw std::runtime_error("Failed to update record");
}

bool CrudService::remove(const std::string& id) {
  return repository_.erase(id);
}

std::vector<Record> CrudService::list() const {
  return repository_.list();
}