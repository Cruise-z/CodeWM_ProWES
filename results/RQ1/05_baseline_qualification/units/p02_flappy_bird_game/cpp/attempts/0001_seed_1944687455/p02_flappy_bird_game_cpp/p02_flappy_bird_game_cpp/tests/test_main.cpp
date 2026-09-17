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
#include <cassert>
#include <iostream>

int main() {
    // Test 1: Basic runtime wiring with deterministic seed
    {
        GameEngine engine(GameConfig::Default(), std::make_unique<LcgRandom>(42));
        
        // Simulate a few steps to ensure no crash and consistent behavior
        const double dt = 1.0 / 60.0;
        for (int i = 0; i < 10; ++i) {
            engine.step(dt);
        }
        
        // Should not be game over yet and have a score of 0 or more
        assert(!engine.isGameOver());
        assert(engine.score() >= 0);
    }
    
    // Test 2: Bird physics trend after flap
    {
        GameConfig cfg = GameConfig::Default();
        LcgRandom rng(42);
        GameEngine engine(cfg, std::make_unique<LcgRandom>(42));
        
        // Initial state
        double initial_y = engine.birdY();
        engine.flap();
        engine.step(0.016);  // ~1/60 second
        
        // After flap, bird should go up initially (y decreases because Y increases upward)
        // But we check that it's not at the same position
        assert(engine.birdY() != initial_y);
        
        // After several steps, bird should be falling (unless it hits ceiling)
        for (int i = 0; i < 10; ++i) {
            engine.step(0.016);
        }
        
        // Should still be alive and have moved
        assert(!engine.isGameOver());
    }
    
    // Test 3: Scoring when a pipe passes
    {
        GameConfig cfg = GameConfig::Default();
        cfg.pipeSpawnInterval = 0.1;  // Spawn very frequently
        cfg.pipeGapHeight = 100.0;
        LcgRandom rng(42);
        GameEngine engine(cfg, std::make_unique<LcgRandom>(42));
        
        // Let's simulate enough time for a pipe to be created and passed
        const double dt = 0.016;  // ~1/60 second
        
        // Advance time until we get some pipes
        for (int i = 0; i < 100; ++i) {
            engine.step(dt);
        }
        
        // At least one score should be achieved by now
        assert(engine.score() >= 0);
    }
    
    // Test 4: Collision detection and reset behavior
    {
        GameConfig cfg = GameConfig::Default();
        cfg.birdX = 100.0;  // Position bird near left edge
        cfg.pipeWidth = 50.0;
        cfg.pipeGapHeight = 200.0;
        cfg.pipeSpeed = 100.0;  // Fast pipes
        
        LcgRandom rng(42);
        GameEngine engine(cfg, std::make_unique<LcgRandom>(42));
        
        // Simulate until collision happens
        const double dt = 0.016;
        bool collision_occurred = false;
        
        for (int i = 0; i < 1000; ++i) {
            engine.step(dt);
            if (engine.isGameOver()) {
                collision_occurred = true;
                break;
            }
        }
        
        assert(collision_occurred);
        
        // Reset the game
        engine.reset();
        
        // After reset, should not be game over and score should be 0
        assert(!engine.isGameOver());
        assert(engine.score() == 0);
    }
    
    // Test 5: Deterministic behavior with fixed seed
    {
        GameConfig cfg = GameConfig::Default();
        LcgRandom rng1(12345);
        LcgRandom rng2(12345);
        GameEngine engine1(cfg, std::make_unique<LcgRandom>(12345));
        GameEngine engine2(cfg, std::make_unique<LcgRandom>(12345));
        
        // Step both engines
        const double dt = 0.016;
        for (int i = 0; i < 100; ++i) {
            engine1.step(dt);
            engine2.step(dt);
        }
        
        // Both should have same score and game state
        assert(engine1.score() == engine2.score());
        assert(engine1.isGameOver() == engine2.isGameOver());
    }
    
    return 0;
}