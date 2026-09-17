#ifndef PIPE_H
#define PIPE_H

#include "GameConfig.h"
#include <algorithm>

/// @brief Pipe entity representing obstacles in the game
class Pipe {
public:
    /// @brief X position of the pipe
    double x;

    /// @brief Y position of the pipe gap center
    double gapY;

    /// @brief Flag indicating if the pipe has been scored
    bool scored;

    /// @brief Construct a new Pipe at given position
    /// @param x0 Initial X position
    /// @param gapY0 Y position of the pipe gap center
    Pipe(double x0, double gapY0) noexcept;

    /// @brief Update pipe position based on time step
    /// @param dt Time step for integration
    /// @param cfg Game configuration containing pipe speed
    void update(double dt, const GameConfig& cfg);

    /// @brief Check if pipe is offscreen (to the left)
    /// @param cfg Game configuration for pipe width
    /// @return True if pipe is completely offscreen to the left
    bool isOffscreen(const GameConfig& cfg) const;

    /// @brief Check if bird has passed this pipe
    /// @param birdX X position of the bird
    /// @param cfg Game configuration for pipe width
    /// @return True if bird has passed the pipe
    bool hasPassedBird(double birdX, const GameConfig& cfg) const;

    /// @brief Check if bird collides with this pipe
    /// @param birdX X position of the bird
    /// @param birdTop Top Y position of the bird
    /// @param birdBottom Bottom Y position of the bird
    /// @param cfg Game configuration for pipe dimensions
    /// @return True if bird collides with pipe (excluding gap)
    bool collidesWithBird(double birdX, double birdTop, double birdBottom, const GameConfig& cfg) const;
};

#endif // PIPE_H