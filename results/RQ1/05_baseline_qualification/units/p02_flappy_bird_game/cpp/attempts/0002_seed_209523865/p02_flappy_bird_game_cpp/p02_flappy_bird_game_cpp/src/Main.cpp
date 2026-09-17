#include <iostream>
#include <iomanip>
#include "GameEngine.h"
#include "GameConfig.h"
#include "Random.h"

int main() {
    // Create game engine with default configuration and seeded random number generator
    GameEngine engine(GameConfig::Default(), std::make_unique<LcgRandom>(42));
    
    // Simulation parameters
    const double dt = 1.0 / 60.0;  // Fixed time step of 1/60 seconds
    const double totalSimulationTime = 5.0;  // Simulate for 5 seconds
    const int flapInterval = 20;  // Flap every 20 frames
    
    // Run simulation
    for (int i = 0; i < static_cast<int>(totalSimulationTime / dt); ++i) {
        // Occasionally flap to keep the bird alive
        if (i % flapInterval == 0) {
            engine.flap();
        }
        
        // Advance the simulation
        engine.step(dt);
        
        // Exit early if game is over
        if (engine.isGameOver()) {
            break;
        }
    }
    
    // Print final results
    std::cout << "Final Score: " << engine.score() << std::endl;
    std::cout << "Game Over: " << (engine.isGameOver() ? "Yes" : "No") << std::endl;
    
    return 0;
}