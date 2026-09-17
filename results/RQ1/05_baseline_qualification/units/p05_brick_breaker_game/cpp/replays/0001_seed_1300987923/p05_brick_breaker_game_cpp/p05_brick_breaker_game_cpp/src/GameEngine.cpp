#include "GameEngine.h"
#include "Collision.h"
#include <cmath>

namespace breakout {

GameEngine::GameEngine(const Playfield& field, const Level& level, const Ball& ball, const Paddle& paddle)
    : field(field)
    , level(level)
    , ball(ball)
    , paddle(paddle)
    , score(0)
    , lives(3) {}

void GameEngine::step(double dt, Input input) {
    // Apply input to paddle
    switch (input) {
        case Left:
            paddle.move(-5.0 * dt, field);
            break;
        case Right:
            paddle.move(5.0 * dt, field);
            break;
        case None:
            // No movement
            break;
    }

    // Integrate ball position
    ball.integrate(dt);

    // Check collision with left/right walls
    if (ball.position.x - ball.radius <= field.left() || ball.position.x + ball.radius >= field.right()) {
        ball.velocity = Collision::reflect(ball.velocity, true, false);
        // Adjust position to prevent tunneling
        if (ball.position.x - ball.radius <= field.left()) {
            ball.position.x = field.left() + ball.radius;
        } else {
            ball.position.x = field.right() - ball.radius;
        }
    }

    // Check collision with top wall
    if (ball.position.y - ball.radius <= field.top()) {
        ball.velocity = Collision::reflect(ball.velocity, false, true);
        // Adjust position to prevent tunneling
        ball.position.y = field.top() + ball.radius;
    }

    // Check collision with bottom wall (lose a life)
    if (ball.position.y + ball.radius >= field.bottom()) {
        --lives;
        // Reset ball to starting position
        ball.position = Vector2(0.0, 0.0);
        ball.velocity = Vector2(0.0, 0.0);
    }

    // Check collision with paddle
    if (Collision::circleVsAABB(ball, paddle.left(), paddle.right(), paddle.top(), paddle.bottom())) {
        ball.velocity = Collision::reflect(ball.velocity, false, true);
        // Adjust position to prevent tunneling
        ball.position.y = paddle.top() - ball.radius;
    }

    // Check collision with bricks
    for (auto& brick : level.bricks) {
        if (!brick.isAlive()) {
            continue;
        }

        if (Collision::circleVsAABB(ball, brick.left(), brick.right(), brick.top(), brick.bottom())) {
            brick.hit();
            ball.velocity = Collision::reflect(ball.velocity, false, true);
            // Adjust position to prevent tunneling
            ball.position.y = brick.top() - ball.radius;

            // Increment score if brick was destroyed
            if (!brick.isAlive()) {
                score += 10;
            }
            break; // Only process one collision per frame
        }
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