#include "Vector2.h"

namespace breakout {

Vector2::Vector2() : x(0.0), y(0.0) {}

Vector2::Vector2(double x, double y) : x(x), y(y) {}

Vector2 Vector2::operator+(Vector2 other) const {
    return Vector2(x + other.x, y + other.y);
}

Vector2 Vector2::operator-(Vector2 other) const {
    return Vector2(x - other.x, y - other.y);
}

Vector2 Vector2::operator*(double scalar) const {
    return Vector2(x * scalar, y * scalar);
}

} // namespace breakout