#ifndef BREAKOUT_BRICK_H
#define BREAKOUT_BRICK_H

#include "Vector2.h"

namespace breakout {

class Brick {
public:
    Vector2 position;
    double width;
    double height;
    int durability;

    Brick(Vector2 pos, double w, double h, int hp);

    bool isAlive() const;
    void hit();
    
    double left() const;
    double right() const;
    double top() const;
    double bottom() const;
};

} // namespace breakout

#endif // BREAKOUT_BRICK_H