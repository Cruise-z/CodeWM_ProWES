#include <cassert>
#include <iostream>

#include "GameEngine.h"
#include "Level.h"
#include "Ball.h"
#include "Paddle.h"
#include "Brick.h"
#include "Collision.h"
#include "Playfield.h"
#include "Vector2.h"

int main() {
    // Test 1: Basic runtime wiring
    // Construct Playfield
    breakout::Playfield field(800.0, 600.0);
    
    // Construct Level
    breakout::Level level;
    level.generateGrid(5, 10, breakout::Vector2(-350.0, -200.0), 
                       breakout::Vector2(70.0, 20.0), 1);
    
    // Construct Ball
    breakout::Ball ball(breakout::Vector2(0.0, 0.0), 
                        breakout::Vector2(100.0, -100.0), 10.0);
    
    // Construct Paddle
    breakout::Paddle paddle(breakout::Vector2(0.0, 250.0), 100.0, 10.0);
    
    // Construct GameEngine
    breakout::GameEngine engine(field, level, ball, paddle);
    
    // Verify initial state
    assert(engine.getScore() == 0);
    assert(engine.getLives() == 3);
    assert(engine.remainingBricks() == 50);  // 5 rows * 10 columns
    assert(level.remaining() == 50);
    
    // Test 2: Collision and scoring
    // Move ball to hit a brick
    // Place ball above a brick at position (0, -200)
    breakout::Ball ball2(breakout::Vector2(0.0, -190.0), 
                         breakout::Vector2(0.0, 100.0), 10.0);
    
    // Create new engine with this ball
    breakout::GameEngine engine2(field, level, ball2, paddle);
    
    // Step once to hit the brick
    engine2.step(0.1, breakout::GameEngine::None);
    
    // Verify score increased and brick removed
    assert(engine2.getScore() == 10);  // 10 points for destroying a brick
    assert(engine2.remainingBricks() == 49);  // One brick destroyed
    assert(level.remaining() == 49);
    
    // Test 3: Reporting
    // Verify remaining bricks count matches
    assert(engine2.remainingBricks() == level.remaining());
    
    // Verify return types
    std::size_t remaining_bricks = engine2.remainingBricks();
    assert(remaining_bricks == 49);
    
    std::cout << "All tests passed!" << std::endl;
    
    return 0;
}