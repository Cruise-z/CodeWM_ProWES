#ifndef INCLUDE_TIME_MONOTONIC_CLOCK_H_
#define INCLUDE_TIME_MONOTONIC_CLOCK_H_

#include "Time/IClock.h"
#include <cstdint>

namespace Time {

/// A monotonic clock adapter that uses the system's steady clock.
/// This clock is not used in tests but provides real-time functionality.
class MonotonicClock : public IClock {
 public:
  /// Constructs a monotonic clock.
  MonotonicClock() = default;

  /// Returns the current time in milliseconds since an unspecified epoch.
  ///
  /// @return The current time in milliseconds.
  std::int64_t now_ms() const noexcept override;
};

}  // namespace Time

#endif  // INCLUDE_TIME_MONOTONIC_CLOCK_H_