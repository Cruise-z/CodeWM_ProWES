#ifndef BREAKOUT_LEVEL_H
#define BREAKOUT_LEVEL_H

#include <cstddef>
#include <vector>
#include "Brick.h"
#include "Vector2.h"

namespace breakout {

class Level {
public:
    std::vector<Brick> bricks;

    Level();

    void generateGrid(int rows, int cols, Vector2 origin, Vector2 cellSize, int hp);
    
    std::size_t remaining() const;
};

} // namespace breakout

#endif // BREAKOUT_LEVEL_H