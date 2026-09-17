#ifndef BREAKOUT_VECTOR2_H
#define BREAKOUT_VECTOR2_H

namespace breakout {

struct Vector2 {
    double x;
    double y;

    // Default constructor
    constexpr Vector2() : x(0.0), y(0.0) {}

    // Parameterized constructor
    constexpr Vector2(double x, double y) : x(x), y(y) {}

    // Addition operator
    constexpr Vector2 operator+(const Vector2& other) const {
        return Vector2(x + other.x, y + other.y);
    }

    // Subtraction operator
    constexpr Vector2 operator-(const Vector2& other) const {
        return Vector2(x - other.x, y - other.y);
    }

    // Scalar multiplication operator
    constexpr Vector2 operator*(double scalar) const {
        return Vector2(x * scalar, y * scalar);
    }
};

} // namespace breakout

#endif // BREAKOUT_VECTOR2_H