#ifndef BIRD_H
#define BIRD_H

#include "GameConfig.h"
#include <algorithm>

/// @brief Bird entity representing the player character in the game
class Bird {
private:
    /// @brief Current Y position of the bird (increases upward)
    double y_;

    /// @brief Current vertical velocity of the bird
    double v_;

public:
    /// @brief Construct a new Bird at given position and velocity
    /// @param y0 Initial Y position
    /// @param v0 Initial vertical velocity
    Bird(double y0, double v0) noexcept;

    /// @brief Apply flap impulse to the bird
    /// @param cfg Game configuration containing flap impulse value
    void flap(const GameConfig& cfg);

    /// @brief Update bird position and velocity based on physics
    /// @param dt Time step for integration
    /// @param cfg Game configuration containing physical constants
    void update(double dt, const GameConfig& cfg);

    /// @brief Get current Y position
    /// @return Current Y position
    double y() const noexcept;

    /// @brief Get current vertical velocity
    /// @return Current vertical velocity
    double velocity() const noexcept;

    /// @brief Calculate top edge of bird bounding box
    /// @param cfg Game configuration for bird dimensions
    /// @return Top Y coordinate of bird
    double top(const GameConfig& cfg) const noexcept;

    /// @brief Calculate bottom edge of bird bounding box
    /// @param cfg Game configuration for bird dimensions
    /// @return Bottom Y coordinate of bird
    double bottom(const GameConfig& cfg) const noexcept;

    /// @brief Reset bird to initial position
    /// @param y0 New Y position to reset to
    void reset(double y0) noexcept;
};

#endif // BIRD_H