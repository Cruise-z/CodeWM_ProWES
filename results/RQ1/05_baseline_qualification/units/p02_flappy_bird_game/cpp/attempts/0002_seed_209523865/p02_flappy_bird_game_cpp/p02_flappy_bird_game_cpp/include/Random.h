#ifndef RANDOM_H_
#define RANDOM_H_

#include <cstdint>

// Interface for random number generation
class IRandom {
public:
    virtual ~IRandom() noexcept = default;
    virtual double nextUnit() = 0;
};

// Linear Congruential Generator implementation
class LcgRandom : public IRandom {
private:
    std::uint64_t state_;

public:
    explicit LcgRandom(std::uint64_t seed);
    
    // Returns a uniform random double in [0, 1)
    double nextUnit() override;
    
    // Returns the next 64-bit random integer
    std::uint64_t nextUint64();
};

#endif // RANDOM_H_