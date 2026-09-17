#ifndef INCLUDE_TIME_ICLOCK_H_
#define INCLUDE_TIME_ICLOCK_H_

#include <cstdint>

namespace Time {

/// Interface for a monotonic clock that provides time in milliseconds.
class IClock {
 public:
  /// Virtual destructor for proper inheritance.
  virtual ~IClock() = default;

  /// Returns the current time in milliseconds since an unspecified epoch.
  ///
  /// @return The current time in milliseconds.
  virtual std::int64_t now_ms() const noexcept = 0;
};

}  // namespace Time

#endif  // INCLUDE_TIME_ICLOCK_H_