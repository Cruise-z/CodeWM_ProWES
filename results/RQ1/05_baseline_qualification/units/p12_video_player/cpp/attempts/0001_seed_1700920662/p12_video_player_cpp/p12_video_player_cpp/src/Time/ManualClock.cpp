#include "Time/ManualClock.h"

namespace Time {

ManualClock::ManualClock(std::int64_t start_ms) : current_ms_(start_ms) {}

void ManualClock::set_now(std::int64_t ms) {
  current_ms_ = ms;
}

void ManualClock::advance(std::int64_t delta_ms) {
  current_ms_ += delta_ms;
}

std::int64_t ManualClock::now_ms() const noexcept {
  return current_ms_;
}

}  // namespace Time