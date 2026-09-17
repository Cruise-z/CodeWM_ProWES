#ifndef GAMECONFIG_H_
#define GAMECONFIG_H_

#include <stdexcept>

// Configuration structure for game parameters
struct GameConfig {
    double worldWidth;
    double worldHeight;
    double gravity;
    double flapImpulse;
    double maxFallSpeed;
    double pipeSpeed;
    double pipeWidth;
    double pipeGapHeight;
    double pipeSpawnInterval;
    double birdX;
    double birdWidth;
    double birdHeight;

    // Factory method to create a default configuration
    static GameConfig Default();

    // Validates the configuration parameters
    // Throws std::invalid_argument if validation fails
    void validate() const;
};

#endif // GAMECONFIG_H_