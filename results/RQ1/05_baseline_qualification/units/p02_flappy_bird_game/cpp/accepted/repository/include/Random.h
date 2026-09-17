#ifndef RANDOM_H_
#define RANDOM_H_

#include <cstdint>

// Interface for random number generation
class IRandom {
 public:
  virtual ~IRandom() noexcept = default;
  // Returns a random double in the range [0, 1)
  virtual double nextUnit() = 0;
};

// Linear Congruential Generator implementation of IRandom
class LcgRandom : public IRandom {
 public:
  // Constructs the generator with the given seed
  explicit LcgRandom(std::uint64_t seed);

  // Returns the next 64-bit unsigned integer in the sequence
  std::uint64_t nextUint64();

  // Returns a random double in the range [0, 1)
  double nextUnit() override;

 private:
  // LCG parameters: a = 6364136223846793005, c = 1
  static constexpr std::uint64_t kA = 6364136223846793005ULL;
  static constexpr std::uint64_t kC = 1ULL;
  
  std::uint64_t state_;
};

#endif  // RANDOM_H_