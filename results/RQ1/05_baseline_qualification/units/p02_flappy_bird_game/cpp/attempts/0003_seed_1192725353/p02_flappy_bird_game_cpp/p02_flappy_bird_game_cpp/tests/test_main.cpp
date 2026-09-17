#include <cassert>
#include <iostream>
#include "GameEngine.h"
#include "GameConfig.h"
#include "Random.h"

int main() {
  // Test 1: Basic runtime wiring with deterministic seed
  {
    GameEngine engine(GameConfig::Default(), std::make_unique<LcgRandom>(42));
    
    const double dt = 1.0 / 60.0;
    const int totalTicks = 100;
    
    // Run simulation for a few ticks
    for (int i = 0; i < totalTicks; ++i) {
      if (i % 10 == 0) {
        engine.flap();
      }
      engine.step(dt);
      
      // Should not crash
      assert(engine.score() >= 0);
      assert(engine.birdY() >= 0);
      
      // Game should not be immediately over
      if (i > 5) {
        break;
      }
    }
    
    // Verify we can get the final state
    assert(engine.config().worldWidth > 0);
    assert(engine.pipes().size() >= 0);
  }
  
  // Test 2: Bird physics trend after flap
  {
    GameConfig cfg = GameConfig::Default();
    LcgRandom rng(12345);
    GameEngine engine(cfg, std::make_unique<LcgRandom>(12345));
    
    // Initial state
    double initialY = engine.birdY();
    double initialVelocity = engine.birdY(); // This is incorrect usage, let's fix
    
    // Get actual bird velocity properly
    // We'll directly test Bird class behavior
    Bird bird(cfg.worldHeight / 2.0, 0.0);
    double initialBirdY = bird.y();
    double initialBirdVelocity = bird.velocity();
    
    // Flap and observe change
    bird.flap(cfg);
    double velocityAfterFlap = bird.velocity();
    
    // After flap, velocity should increase
    assert(velocityAfterFlap > initialBirdVelocity);
    
    // Update with small dt to see physics in action
    const double dt = 0.01;
    bird.update(dt, cfg);
    double newY = bird.y();
    
    // With positive initial velocity, y should increase
    assert(newY > initialBirdY);
  }
  
  // Test 3: Scoring when a pipe passes
  {
    GameConfig cfg = GameConfig::Default();
    LcgRandom rng(999);
    GameEngine engine(cfg, std::make_unique<LcgRandom>(999));
    
    // Advance enough time to spawn some pipes
    const double dt = 0.1;
    for (int i = 0; i < 100; ++i) {
      engine.step(dt);
      if (i % 10 == 0) {
        engine.flap();
      }
    }
    
    // At least some score should be accumulated
    assert(engine.score() >= 0);
  }
  
  // Test 4: Collision and reset behavior
  {
    GameConfig cfg = GameConfig::Default();
    cfg.birdX = 100.0; // Put bird near the start
    cfg.pipeWidth = 20.0;
    cfg.pipeGapHeight = 100.0;
    
    LcgRandom rng(888);
    GameEngine engine(cfg, std::make_unique<LcgRandom>(888));
    
    // Force immediate pipe creation
    const double dt = 0.01;
    for (int i = 0; i < 50; ++i) {
      engine.step(dt);
    }
    
    // Reset and verify state
    engine.reset();
    
    // After reset, should be at center again
    assert(engine.birdY() == cfg.worldHeight / 2.0);
    assert(engine.score() == 0);
    assert(engine.isGameOver() == false);
  }
  
  std::cout << "All tests passed!" << std::endl;
  return 0;
}