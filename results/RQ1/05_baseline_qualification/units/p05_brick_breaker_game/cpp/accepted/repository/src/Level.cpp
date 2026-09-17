#include "Level.h"

namespace breakout {

Level::Level() = default;

void Level::generateGrid(int rows, int cols, Vector2 origin, Vector2 cellSize, int hp) {
    bricks.clear();
    
    for (int row = 0; row < rows; ++row) {
        for (int col = 0; col < cols; ++col) {
            Vector2 position(
                origin.x + col * cellSize.x,
                origin.y + row * cellSize.y
            );
            bricks.emplace_back(position, cellSize.x, cellSize.y, hp);
        }
    }
}

std::size_t Level::remaining() const {
    std::size_t count = 0;
    for (const auto& brick : bricks) {
        if (brick.isAlive()) {
            ++count;
        }
    }
    return count;
}

} // namespace breakout