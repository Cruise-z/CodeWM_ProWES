#include "IRandom.h"

namespace snake {

DefaultRandom::DefaultRandom(std::uint32_t seed) : engine_(seed) {}

std::size_t DefaultRandom::next(std::size_t maxExclusive) {
  if (maxExclusive == 0) {
    return 0;
  }
  std::uniform_int_distribution<std::size_t> dist(0, maxExclusive - 1);
  return dist(engine_);
}

}  // namespace snake