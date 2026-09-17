#include "Ball.h"

namespace breakout {

Ball::Ball(Vector2 p, Vector2 v, double r) 
    : position(p), velocity(v), radius(r) {}

void Ball::integrate(double dt) {
    position = position + velocity * dt;
}

} // namespace breakout