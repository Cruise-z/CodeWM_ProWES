#include "Playfield.h"

namespace breakout {

Playfield::Playfield(double w, double h) : width(w), height(h) {}

double Playfield::left() const {
    return -width / 2.0;
}

double Playfield::right() const {
    return width / 2.0;
}

double Playfield::top() const {
    return -height / 2.0;
}

double Playfield::bottom() const {
    return height / 2.0;
}

} // namespace breakout