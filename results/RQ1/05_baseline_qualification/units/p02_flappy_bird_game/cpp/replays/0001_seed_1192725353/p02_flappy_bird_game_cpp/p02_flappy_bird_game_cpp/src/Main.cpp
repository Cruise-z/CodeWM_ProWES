#include <iostream>
#include <iomanip>
#include "GameEngine.h"
#include "GameConfig.h"
#include "Random.h"

int main() {
  // Create game engine with default configuration and seeded random number generator
  GameEngine engine(GameConfig::Default(), std::make_unique<LcgRandom>(42));
  
  // Simulation parameters
  const double dt = 1.0 / 60.0;  // Fixed time step
  const int totalTicks = 300;    // Simulate for ~5 seconds (300 * 1/60s = 5s)
  
  // Run simulation
  for (int i = 0; i < totalTicks; ++i) {
    // Flap every 10 ticks to keep the bird moving
    if (i % 10 == 0) {
      engine.flap();
    }
    
    // Advance game state
    engine.step(dt);
    
    // Exit early if game is over
    if (engine.isGameOver()) {
      break;
    }
  }
  
  // Print final game state
  std::cout << "Final Score: " << engine.score() << std::endl;
  std::cout << "Game Over: " << (engine.isGameOver() ? "Yes" : "No") << std::endl;
  
  return 0;
}