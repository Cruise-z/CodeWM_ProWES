#include "Random.h"
#include <limits>

// LCG parameters: a = 6364136223846793005, c = 1
constexpr std::uint64_t LcgRandom::kA;
constexpr std::uint64_t LcgRandom::kC;

LcgRandom::LcgRandom(std::uint64_t seed) : state_(seed) {}

std::uint64_t LcgRandom::nextUint64() {
  state_ = kA * state_ + kC;
  return state_;
}

double LcgRandom::nextUnit() {
  return static_cast<double>(nextUint64()) / 
         (std::numeric_limits<std::uint64_t>::max() + 1.0);
}