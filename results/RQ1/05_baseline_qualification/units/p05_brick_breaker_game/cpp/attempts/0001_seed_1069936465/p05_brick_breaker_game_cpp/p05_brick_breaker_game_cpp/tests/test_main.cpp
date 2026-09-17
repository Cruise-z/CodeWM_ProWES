#include <cassert>
#include "GameEngine.h"
#include "Level.h"
#include "Ball.h"
#include "Paddle.h"
#include "Playfield.h"
#include "Vector2.h"

int main() {
    // Test basic runtime wiring
    breakout::Playfield field(800.0, 600.0);
    breakout::Level level;
    level.generateGrid(5, 10, breakout::Vector2(-350.0, -200.0), breakout::Vector2(70.0, 30.0), 1);
    breakout::Ball ball(breakout::Vector2(0.0, 0.0), breakout::Vector2(100.0, -100.0), 10.0);
    breakout::Paddle paddle(breakout::Vector2(0.0, 250.0), 100.0, 10.0);
    breakout::GameEngine engine(field, level, ball, paddle);
    
    // Verify initial state
    assert(engine.getScore() == 0);
    assert(engine.getLives() == 3);
    assert(engine.remainingBricks() == 50); // 5 rows * 10 columns
    assert(level.remaining() == 50);
    
    // Test collision and scoring
    // Move ball to hit a brick
    // Position the ball so it will hit the first brick (at (-350, -200))
    breakout::Ball testBall(breakout::Vector2(-330.0, -180.0), breakout::Vector2(0.0, 100.0), 10.0);
    breakout::Paddle testPaddle(breakout::Vector2(0.0, 250.0), 100.0, 10.0);
    breakout::GameEngine testEngine(field, level, testBall, testPaddle);
    
    // Step once to hit the brick
    testEngine.step(0.1, breakout::GameEngine::None);
    
    // Verify that brick is destroyed and score incremented
    assert(testEngine.getScore() == 10);
    assert(testEngine.remainingBricks() == 49);
    assert(level.remaining() == 49);
    
    // Verify that the brick is actually dead
    assert(level.bricks[0].isAlive() == false);
    
    return 0;
}