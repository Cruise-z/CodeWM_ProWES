#include "Paddle.h"

namespace breakout {

Paddle::Paddle(Vector2 pos, double w, double h)
    : position(pos), width(w), height(h) {}

void Paddle::move(double dx, const Playfield& f) {
    position.x += dx;
    
    // Clamp to playfield boundaries
    const double leftBound = f.left() + width / 2.0;
    const double rightBound = f.right() - width / 2.0;
    
    if (position.x < leftBound) {
        position.x = leftBound;
    } else if (position.x > rightBound) {
        position.x = rightBound;
    }
}

double Paddle::left() const {
    return position.x - width / 2.0;
}

double Paddle::right() const {
    return position.x + width / 2.0;
}

double Paddle::top() const {
    return position.y - height / 2.0;
}

double Paddle::bottom() const {
    return position.y + height / 2.0;
}

} // namespace breakout