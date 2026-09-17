#pragma once

#include <cstdint>

class ManualClock {
 public:
  explicit ManualClock(std::uint64_t initial);

  std::uint64_t now() const noexcept;

  void advance(std::uint64_t delta) noexcept;

 private:
  std::uint64_t current_;
};