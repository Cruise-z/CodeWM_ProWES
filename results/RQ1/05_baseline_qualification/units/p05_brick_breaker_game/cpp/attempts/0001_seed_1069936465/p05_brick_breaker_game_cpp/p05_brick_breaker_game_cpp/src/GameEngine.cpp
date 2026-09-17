#include "GameEngine.h"
#include "Collision.h"
#include <cmath>

namespace breakout {

GameEngine::GameEngine(const Playfield& field, const Level& level, const Ball& ball, const Paddle& paddle)
    : field(field), level(level), ball(ball), paddle(paddle), score(0), lives(3) {}

void GameEngine::step(double dt, Input input) {
    // Apply input to paddle
    if (input == Left) {
        paddle.move(-5.0 * dt, field);
    } else if (input == Right) {
        paddle.move(5.0 * dt, field);
    }
    
    // Integrate ball position
    ball.integrate(dt);
    
    // Check collision with walls
    if (ball.position.x - ball.radius <= field.left() || ball.position.x + ball.radius >= field.right()) {
        ball.velocity.x = -ball.velocity.x;
    }
    if (ball.position.y - ball.radius <= field.top()) {
        ball.velocity.y = -ball.velocity.y;
    }
    
    // Check collision with paddle
    if (Collision::circleVsAABB(ball, paddle.left(), paddle.right(), paddle.top(), paddle.bottom())) {
        // Reflect ball velocity vertically
        ball.velocity = Collision::reflect(ball.velocity, false, true);
        
        // Add some horizontal velocity based on where the ball hits the paddle
        double hitPosition = (ball.position.x - paddle.left()) / (paddle.right() - paddle.left());
        ball.velocity.x += (hitPosition - 0.5) * 2.0;
    }
    
    // Check collision with bricks
    for (auto& brick : level.bricks) {
        if (!brick.isAlive()) continue;
        
        if (Collision::circleVsAABB(ball, brick.left(), brick.right(), brick.top(), brick.bottom())) {
            brick.hit();
            
            // Increment score
            score += 10;
            
            // Reflect ball velocity
            // Determine which side was hit based on relative positions
            double ballCenterX = ball.position.x;
            double ballCenterY = ball.position.y;
            double brickLeft = brick.left();
            double brickRight = brick.right();
            double brickTop = brick.top();
            double brickBottom = brick.bottom();
            
            // Calculate distances to each side
            double distLeft = std::abs(ballCenterX - brickLeft);
            double distRight = std::abs(ballCenterX - brickRight);
            double distTop = std::abs(ballCenterY - brickTop);
            double distBottom = std::abs(ballCenterY - brickBottom);
            
            // Find minimum distance
            double minDist = std::min({distLeft, distRight, distTop, distBottom});
            
            // Reflect based on which side was hit
            if (minDist == distLeft || minDist == distRight) {
                ball.velocity.x = -ball.velocity.x;
            } else {
                ball.velocity.y = -ball.velocity.y;
            }
            
            // Break out of loop since we only want to handle one collision per frame
            break;
        }
    }
    
    // Check if ball is out of bounds (bottom of playfield)
    if (ball.position.y - ball.radius > field.bottom()) {
        lives--;
        
        // Reset ball position for next life
        ball.position = Vector2(0.0, 0.0);
        ball.velocity = Vector2(0.0, 0.0);
    }
}

bool GameEngine::isLevelCleared() const {
    return level.remaining() == 0;
}

std::size_t GameEngine::remainingBricks() const {
    return level.remaining();
}

int GameEngine::getScore() const {
    return score;
}

int GameEngine::getLives() const {
    return lives;
}

} // namespace breakout