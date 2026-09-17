#pragma once

#include <map>
#include <optional>
#include <string>
#include <vector>
#include "Record.h"

class Repository {
 public:
  bool insert(const Record& record);
  std::optional<Record> find(const std::string& id) const;
  bool replace(const Record& record);
  bool erase(const std::string& id);
  std::vector<Record> list() const;

 private:
  std::map<std::string, Record> records_;
};