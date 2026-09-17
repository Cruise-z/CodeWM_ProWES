#ifndef BREAKOUT_COLLISION_H
#define BREAKOUT_COLLISION_H

#include "Ball.h"
#include "Vector2.h"

namespace breakout {

class Collision {
public:
    /// Detects collision between a ball and an axis-aligned bounding box
    /// \param b The ball to test
    /// \param left Left boundary of the AABB
    /// \param right Right boundary of the AABB
    /// \param top Top boundary of the AABB
    /// \param bottom Bottom boundary of the AABB
    /// \return True if the ball intersects the AABB
    static bool circleVsAABB(const Ball& b, double left, double right, double top, double bottom);

    /// Reflects a velocity vector off a surface
    /// \param v The incident velocity vector
    /// \param flipX If true, reverse the x-component
    /// \param flipY If true, reverse the y-component
    /// \return The reflected velocity vector
    static Vector2 reflect(const Vector2& v, bool flipX, bool flipY);
};

} // namespace breakout

#endif // BREAKOUT_COLLISION_H