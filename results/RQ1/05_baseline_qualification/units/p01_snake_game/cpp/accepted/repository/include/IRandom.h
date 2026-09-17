#ifndef SNAKE_IRANDOM_H_
#define SNAKE_IRANDOM_H_

#include <cstddef>
#include <cstdint>
#include <random>

namespace snake {

/// Interface for random number generation
class IRandom {
 public:
  virtual ~IRandom() = default;

  /// Returns a random integer in the range [0, maxExclusive)
  /// @param maxExclusive The upper bound (exclusive) for the generated number
  /// @return A random integer in [0, maxExclusive)
  virtual std::size_t next(std::size_t maxExclusive) = 0;
};

/// Default implementation of IRandom using std::mt19937
class DefaultRandom final : public IRandom {
 public:
  /// Constructs a new DefaultRandom with the given seed
  /// @param seed The seed for the random number generator
  explicit DefaultRandom(std::uint32_t seed);

  /// Generates a random number in the range [0, maxExclusive)
  /// @param maxExclusive The upper bound (exclusive) for the generated number
  /// @return A random integer in [0, maxExclusive)
  std::size_t next(std::size_t maxExclusive) override;

 private:
  std::mt19937 engine_;
};

}  // namespace snake

#endif  // SNAKE_IRANDOM_H_