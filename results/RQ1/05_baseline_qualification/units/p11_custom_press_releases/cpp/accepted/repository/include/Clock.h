#ifndef CLOCK_H
#define CLOCK_H

#include <string>

/// @brief Abstract interface for time retrieval
class Clock {
public:
    /// @brief Virtual destructor for proper inheritance
    virtual ~Clock() = default;

    /// @brief Returns current timestamp as string
    /// @return Current timestamp in ISO format
    virtual std::string now() const = 0;
};

/// @brief Fixed-clock implementation for deterministic testing
class FixedClock : public Clock {
private:
    /// @brief Timestamp stored for deterministic returns
    std::string timestamp_;

public:
    /// @brief Constructor initializes the fixed timestamp
    /// @param timestamp The fixed timestamp to return
    explicit FixedClock(const std::string& timestamp);

    /// @brief Returns the fixed timestamp
    /// @return The fixed timestamp provided at construction
    std::string now() const override;
};

#endif // CLOCK_H