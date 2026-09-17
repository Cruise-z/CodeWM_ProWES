#include "GameEngine.h"
#include "Playfield.h"
#include "Level.h"
#include "Ball.h"
#include "Paddle.h"
#include "Vector2.h"
#include <iostream>

int main() {
    // Create playfield
    breakout::Playfield field(800.0, 600.0);
    
    // Create level
    breakout::Level level;
    level.generateGrid(5, 10, breakout::Vector2(-350.0, -200.0), 
                       breakout::Vector2(70.0, 20.0), 1);
    
    // Create ball
    breakout::Ball ball(breakout::Vector2(0.0, 0.0), 
                        breakout::Vector2(100.0, -100.0), 10.0);
    
    // Create paddle
    breakout::Paddle paddle(breakout::Vector2(0.0, 250.0), 100.0, 10.0);
    
    // Create game engine
    breakout::GameEngine engine(field, level, ball, paddle);
    
    // Simulate a few steps
    for (int i = 0; i < 10; ++i) {
        engine.step(0.1, breakout::GameEngine::None);
    }
    
    // Print summary
    std::cout << "Score: " << engine.getScore() << std::endl;
    std::cout << "Lives: " << engine.getLives() << std::endl;
    std::cout << "Remaining bricks: " << engine.remainingBricks() << std::endl;
    
    return 0;
}