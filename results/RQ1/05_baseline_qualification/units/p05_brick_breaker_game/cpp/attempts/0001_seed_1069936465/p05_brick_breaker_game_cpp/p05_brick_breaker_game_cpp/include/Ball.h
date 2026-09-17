#ifndef BREAKOUT_BALL_H
#define BREAKOUT_BALL_H

#include "Vector2.h"

namespace breakout {

class Ball {
public:
    Vector2 position;
    Vector2 velocity;
    double radius;

    Ball(Vector2 p, Vector2 v, double r);

    void integrate(double dt);
};

} // namespace breakout

#endif // BREAKOUT_BALL_H