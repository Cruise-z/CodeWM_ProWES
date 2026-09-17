#include "Brick.h"

namespace breakout {

Brick::Brick(Vector2 pos, double w, double h, int hp)
    : position(pos), width(w), height(h), durability(hp) {}

bool Brick::isAlive() const {
    return durability > 0;
}

void Brick::hit() {
    if (durability > 0) {
        --durability;
    }
}

double Brick::left() const {
    return position.x - width / 2.0;
}

double Brick::right() const {
    return position.x + width / 2.0;
}

double Brick::top() const {
    return position.y - height / 2.0;
}

double Brick::bottom() const {
    return position.y + height / 2.0;
}

} // namespace breakout