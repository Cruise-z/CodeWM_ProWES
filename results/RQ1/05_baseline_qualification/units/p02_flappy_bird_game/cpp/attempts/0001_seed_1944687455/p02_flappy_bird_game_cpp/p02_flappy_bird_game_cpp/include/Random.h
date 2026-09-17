#ifndef RANDOM_H
#define RANDOM_H

#include <cstdint>

/// @brief Interface for random number generation
class IRandom {
public:
    /// @brief Virtual destructor for proper inheritance
    virtual ~IRandom() noexcept = default;

    /// @brief Generate a random double in the range [0, 1)
    /// @return Random double in [0, 1)
    virtual double nextUnit() = 0;
};

/// @brief Linear Congruential Generator implementation of IRandom
class LcgRandom : public IRandom {
private:
    /// @brief Internal state of the generator
    std::uint64_t state_;

public:
    /// @brief Construct a new LcgRandom with given seed
    /// @param seed Initial seed value
    explicit LcgRandom(std::uint64_t seed);

    /// @brief Generate the next 64-bit random unsigned integer
    /// @return Next random 64-bit unsigned integer
    std::uint64_t nextUint64();

    /// @brief Generate a random double in the range [0, 1)
    /// @return Random double in [0, 1)
    double nextUnit() override;
};

#endif // RANDOM_H