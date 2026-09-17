#ifndef BREAKOUT_VECTOR2_H
#define BREAKOUT_VECTOR2_H

namespace breakout {

struct Vector2 {
    double x;
    double y;

    Vector2();
    Vector2(double x, double y);

    Vector2 operator+(Vector2 other) const;
    Vector2 operator-(Vector2 other) const;
    Vector2 operator*(double scalar) const;
};

} // namespace breakout

#endif // BREAKOUT_VECTOR2_H