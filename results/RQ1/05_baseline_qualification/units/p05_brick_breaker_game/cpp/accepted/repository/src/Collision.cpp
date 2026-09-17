#include "Collision.h"
#include <cmath>

namespace breakout {

bool Collision::circleVsAABB(const Ball& b, double left, double right, double top, double bottom) {
    // Find the closest point to the circle within the rectangle
    double closestX = std::max(left, std::min(b.position.x, right));
    double closestY = std::max(top, std::min(b.position.y, bottom));

    // Calculate the distance between the circle's center and this closest point
    double distanceX = b.position.x - closestX;
    double distanceY = b.position.y - closestY;

    // If the distance is less than the circle's radius, an intersection occurs
    double distanceSquared = (distanceX * distanceX) + (distanceY * distanceY);
    return distanceSquared < (b.radius * b.radius);
}

Vector2 Collision::reflect(const Vector2& v, bool flipX, bool flipY) {
    double newX = flipX ? -v.x : v.x;
    double newY = flipY ? -v.y : v.y;
    return Vector2(newX, newY);
}

} // namespace breakout