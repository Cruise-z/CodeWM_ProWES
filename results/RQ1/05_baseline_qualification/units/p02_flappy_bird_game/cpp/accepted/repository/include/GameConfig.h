#ifndef GAMECONFIG_H_
#define GAMECONFIG_H_

#include <stdexcept>

// Configuration struct for game parameters
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

  // Creates a default configuration with sane values
  static GameConfig Default();

  // Validates that all configuration values are valid
  // Throws std::invalid_argument if validation fails
  void validate() const;
};

#endif  // GAMECONFIG_H_