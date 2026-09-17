#ifndef GAMEENGINE_H_
#define GAMEENGINE_H_

#include <memory>
#include "GameConfig.h"
#include "GameState.h"
#include "Random.h"

// GameEngine is the main facade that orchestrates the game state,
// configuration, and random number generation
class GameEngine {
 public:
  // Constructs a new game engine with the given configuration and random number generator
  GameEngine(GameConfig cfg, std::unique_ptr<IRandom> rng);

  // Resets the game state to its initial conditions
  void reset();

  // Makes the bird flap if the game is not over
  void flap();

  // Advances the game state by the given time delta
  void step(double dt);

  // Returns the current score
  int score() const noexcept;

  // Returns true if the game is over
  bool isGameOver() const noexcept;

  // Returns the current y position of the bird
  double birdY() const noexcept;

  // Returns a constant reference to the vector of pipes
  const std::vector<Pipe>& pipes() const noexcept;

  // Returns a constant reference to the game configuration
  const GameConfig& config() const noexcept;

 private:
  GameConfig cfg_;                           // Game configuration
  std::unique_ptr<IRandom> rng_;             // Random number generator
  GameState state_;                          // Game state management
};

#endif  // GAMEENGINE_H_