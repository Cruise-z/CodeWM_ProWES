#ifndef INCLUDE_TIME_MANUAL_CLOCK_H_
#define INCLUDE_TIME_MANUAL_CLOCK_H_

#include "Time/IClock.h"
#include <cstdint>

namespace Time {

/// A deterministic manual clock for testing purposes.
/// Allows explicit control over the passage of time.
class ManualClock : public IClock {
 public:
  /// Constructs a manual clock starting at the given time.
  ///
  /// @param start_ms The initial time in milliseconds.
  explicit ManualClock(std::int64_t start_ms);

  /// Sets the current time of the clock.
  ///
  /// @param ms The new time in milliseconds.
  void set_now(std::int64_t ms);

  /// Advances the clock by the given delta.
  ///
  /// @param delta_ms The amount of time to advance in milliseconds.
  void advance(std::int64_t delta_ms);

  /// Returns the current time in milliseconds.
  ///
  /// @return The current time in milliseconds.
  std::int64_t now_ms() const noexcept override;

 private:
  std::int64_t current_ms_;
};

}  // namespace Time

#endif  // INCLUDE_TIME_MANUAL_CLOCK_H_