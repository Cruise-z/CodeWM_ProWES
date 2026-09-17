#pragma once

#include <cstdint>
#include <string>

struct Record {
  std::string id;
  std::string name;
  std::string email;
  std::uint64_t revision;
  std::uint64_t updated_at;

  Record(std::string id, std::string name, std::string email, std::uint64_t revision, std::uint64_t updated_at)
      : id(std::move(id)),
        name(std::move(name)),
        email(std::move(email)),
        revision(revision),
        updated_at(updated_at) {}

  bool operator==(const Record& other) const {
    return id == other.id && name == other.name && email == other.email &&
           revision == other.revision && updated_at == other.updated_at;
  }
};