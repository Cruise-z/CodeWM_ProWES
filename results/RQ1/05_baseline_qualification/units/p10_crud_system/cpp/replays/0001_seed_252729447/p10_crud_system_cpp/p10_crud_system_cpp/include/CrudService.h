#pragma once

#include <optional>
#include <string>
#include <vector>
#include "ManualClock.h"
#include "Record.h"
#include "Repository.h"

class CrudService {
 public:
  CrudService(Repository& repository, ManualClock& clock);

  Record create(const std::string& id, const std::string& name, const std::string& email);
  std::optional<Record> get(const std::string& id) const;
  Record update(const std::string& id, const std::string& name, const std::string& email);
  bool remove(const std::string& id);
  std::vector<Record> list() const;

 private:
  Repository& repository_;
  ManualClock& clock_;
};