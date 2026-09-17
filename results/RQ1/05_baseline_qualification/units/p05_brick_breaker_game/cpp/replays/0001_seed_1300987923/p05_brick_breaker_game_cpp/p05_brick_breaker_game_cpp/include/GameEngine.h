#ifndef BREAKOUT_GAMEENGINE_H
#define BREAKOUT_GAMEENGINE_H

#include <cstddef>
#include <vector>
#include "Playfield.h"
#include "Level.h"
#include "Ball.h"
#include "Paddle.h"

namespace breakout {

class GameEngine {
public:
    enum Input { Left, Right, None };

    GameEngine(const Playfield& field, const Level& level, const Ball& ball, const Paddle& paddle);

    void step(double dt, Input input);
    bool isLevelCleared() const;
    std::size_t remainingBricks() const;
    int getScore() const;
    int getLives() const;

private:
    Playfield field;
    Level level;
    Ball ball;
    Paddle paddle;
    int score;
    int lives;
};

} // namespace breakout

#endif // BREAKOUT_GAMEENGINE_H