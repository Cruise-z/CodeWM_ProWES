#ifndef BREAKOUT_COLLISION_H
#define BREAKOUT_COLLISION_H

#include "Ball.h"
#include "Vector2.h"

namespace breakout {

class Collision {
public:
    static bool circleVsAABB(const Ball& b, double left, double right, double top, double bottom);
    static Vector2 reflect(const Vector2& v, bool flipX, bool flipY);
};

} // namespace breakout

#endif // BREAKOUT_COLLISION_H