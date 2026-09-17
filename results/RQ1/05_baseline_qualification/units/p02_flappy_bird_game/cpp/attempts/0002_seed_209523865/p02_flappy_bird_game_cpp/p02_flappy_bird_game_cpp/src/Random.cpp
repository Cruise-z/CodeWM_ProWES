#include "Random.h"
#include <limits>

// LCG parameters
static constexpr std::uint64_t LCG_A = 6364136223846793005ULL;
static constexpr std::uint64_t LCG_C = 1ULL;

LcgRandom::LcgRandom(std::uint64_t seed) : state_(seed) {}

std::uint64_t LcgRandom::nextUint64() {
    state_ = LCG_A * state_ + LCG_C;
    return state_;
}

double LcgRandom::nextUnit() {
    return static_cast<double>(nextUint64()) / 
           static_cast<double>(std::numeric_limits<std::uint64_t>::max() + 1ULL);
}