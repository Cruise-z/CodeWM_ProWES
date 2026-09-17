#include "Geometry.h"

bool Geometry::inBounds(Point point, Size size) {
    return point.x >= 0 && point.x < size.width && point.y >= 0 && point.y < size.height;
}

Point Geometry::advance(Point point, Direction direction) {
    switch (direction) {
        case Direction::Up:
            point.y--;
            break;
        case Direction::Right:
            point.x++;
            break;
        case Direction::Down:
            point.y++;
            break;
        case Direction::Left:
            point.x--;
            break;
    }
    return point;
}

Direction Geometry::rotateLeft(Direction direction) {
    return static_cast<Direction>((static_cast<int8_t>(direction) + 3) % 4);
}

Direction Geometry::rotateRight(Direction direction) {
    return static_cast<Direction>((static_cast<int8_t>(direction) + 1) % 4);
}