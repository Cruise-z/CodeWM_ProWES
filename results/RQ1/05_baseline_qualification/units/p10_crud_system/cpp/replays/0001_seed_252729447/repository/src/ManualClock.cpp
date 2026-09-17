#include "ManualClock.h"

ManualClock::ManualClock(std::uint64_t initial) : current_(initial) {}

std::uint64_t ManualClock::now() const noexcept {
  return current_;
}

void ManualClock::advance(std::uint64_t delta) noexcept {
  current_ += delta;
}