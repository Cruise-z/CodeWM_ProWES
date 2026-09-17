#ifndef BREAKOUT_PADDLE_H
#define BREAKOUT_PADDLE_H

#include "Vector2.h"
#include "Playfield.h"

namespace breakout {

class Paddle {
public:
    Vector2 position;
    double width;
    double height;

    Paddle(Vector2 pos, double w, double h);

    void move(double dx, const Playfield& f);
    double left() const;
    double right() const;
    double top() const;
    double bottom() const;
};

} // namespace breakout

#endif // BREAKOUT_PADDLE_H