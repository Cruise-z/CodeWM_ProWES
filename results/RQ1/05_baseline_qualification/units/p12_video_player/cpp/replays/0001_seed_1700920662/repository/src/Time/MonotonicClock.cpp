#include "Time/MonotonicClock.h"
#include <chrono>

namespace Time {

std::int64_t MonotonicClock::now_ms() const noexcept {
  const auto now = std::chrono::steady_clock::now();
  const auto duration = now.time_since_epoch();
  const auto millis = std::chrono::duration_cast<std::chrono::milliseconds>(duration);
  return millis.count();
}

}  // namespace Time