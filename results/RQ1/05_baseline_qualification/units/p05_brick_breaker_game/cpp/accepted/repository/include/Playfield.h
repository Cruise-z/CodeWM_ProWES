#ifndef BREAKOUT_PLAYFIELD_H
#define BREAKOUT_PLAYFIELD_H

#include <cstddef>

namespace breakout {

class Playfield {
public:
    double width;
    double height;

    explicit Playfield(double w, double h);

    double left() const;
    double right() const;
    double top() const;
    double bottom() const;
};

} // namespace breakout

#endif // BREAKOUT_PLAYFIELD_H