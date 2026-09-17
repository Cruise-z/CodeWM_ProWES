#ifndef GAMESTATE_H_
#define GAMESTATE_H_

#include <vector>
#include <memory>
#include "Bird.h"
#include "Pipe.h"
#include "GameConfig.h"

// Forward declaration of IRandom to avoid including its header
class IRandom;

// GameState orchestrates the game state including the bird, pipes, score, and game over condition
class GameState {
 public:
  // Constructs a new game state with the given configuration
  explicit GameState(GameConfig cfg);

  // Resets the game state to its initial conditions
  void reset();

  // Makes the bird flap if the game is not over
  void flap();

  // Updates the game state by the given time delta
  void update(double dt, IRandom& rng);

  // Returns the current score
  int score() const noexcept;

  // Returns true if the game is over
  bool gameOver() const noexcept;

  // Returns a constant reference to the vector of pipes
  const std::vector<Pipe>& pipes() const noexcept;

  // Returns the current y position of the bird
  double birdY() const noexcept;

  // Returns the top edge of the bird's bounding box
  double birdTop() const noexcept;

  // Returns the bottom edge of the bird's bounding box
  double birdBottom() const noexcept;

 private:
  GameConfig cfg_;                           // Game configuration
  Bird bird_;                                // Bird entity
  std::vector<Pipe> pipes_;                  // Vector of pipe entities
  int score_;                                // Current score
  bool gameOver_;                            // Flag indicating if the game is over
  double timeSinceLastPipe_;                 // Time since the last pipe was spawned
};

#endif  // GAMESTATE_H_