/*
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "GameEngine.h"
#include "GameConfig.h"
#include "Random.h"
#include <iostream>
#include <iomanip>

int main() {
    // Create game engine with default configuration and seeded random number generator
    GameEngine engine(GameConfig::Default(), std::make_unique<LcgRandom>(42));
    
    // Simulation parameters
    const double dt = 1.0 / 60.0;  // Fixed time step of 1/60 seconds
    const double totalSimulationTime = 5.0;  // Simulate for 5 seconds
    const double flapInterval = 0.5;  // Flap every 0.5 seconds
    
    // Run simulation
    double currentTime = 0.0;
    double lastFlapTime = 0.0;
    
    while (currentTime < totalSimulationTime && !engine.isGameOver()) {
        // Perform flap if it's time
        if (currentTime - lastFlapTime >= flapInterval) {
            engine.flap();
            lastFlapTime = currentTime;
        }
        
        // Step the game forward
        engine.step(dt);
        currentTime += dt;
    }
    
    // Print final results
    std::cout << "Final Score: " << engine.score() << std::endl;
    std::cout << "Game Over: " << (engine.isGameOver() ? "Yes" : "No") << std::endl;
    
    return 0;
}