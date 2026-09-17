#ifndef GAMECONFIG_H
#define GAMECONFIG_H

#include <stdexcept>

/// @brief Configuration structure for game parameters
struct GameConfig {
    /// @brief Width of the game world
    double worldWidth;

    /// @brief Height of the game world
    double worldHeight;

    /// @brief Gravity constant affecting bird falling speed
    double gravity;

    /// @brief Impulse applied when bird flaps
    double flapImpulse;

    /// @brief Maximum speed at which bird can fall
    double maxFallSpeed;

    /// @brief Speed at which pipes move leftward
    double pipeSpeed;

    /// @brief Width of each pipe
    double pipeWidth;

    /// @brief Height of the gap between pipes
    double pipeGapHeight;

    /// @brief Time interval between pipe spawns
    double pipeSpawnInterval;

    /// @brief X position of the bird
    double birdX;

    /// @brief Width of the bird
    double birdWidth;

    /// @brief Height of the bird
    double birdHeight;

    /// @brief Factory method to create a default configuration
    /// @return Default GameConfig with sane values
    static GameConfig Default();

    /// @brief Validate configuration parameters
    /// @throws std::invalid_argument if any parameter is invalid
    void validate() const;
};

#endif // GAMECONFIG_H