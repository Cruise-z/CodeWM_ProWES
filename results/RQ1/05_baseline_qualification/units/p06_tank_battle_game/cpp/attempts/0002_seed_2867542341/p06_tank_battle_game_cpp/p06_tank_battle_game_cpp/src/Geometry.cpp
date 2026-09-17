#include "Geometry.h"

bool Geometry::inBounds(Point point, Size size) {
    return (point.x >= 0 && point.x < size.width && point.y >= 0 && point.y < size.height);
}

Point Geometry::advance(Point point, Direction direction) {
    switch (direction) {
        case Direction::Up:
            return Point(point.x, point.y - 1);
        case Direction::Right:
            return Point(point.x + 1, point.y);
        case Direction::Down:
            return Point(point.x, point.y + 1);
        case Direction::Left:
            return Point(point.x - 1, point.y);
    }
    // This should never be reached, but added to satisfy compiler
    return point;
}

Direction Geometry::rotateLeft(Direction direction) {
    switch (direction) {
        case Direction::Up:
            return Direction::Left;
        case Direction::Right:
            return Direction::Up;
        case Direction::Down:
            return Direction::Right;
        case Direction::Left:
            return Direction::Down;
    }
    // This should never be reached, but added to satisfy compiler
    return direction;
}

Direction Geometry::rotateRight(Direction direction) {
    switch (direction) {
        case Direction::Up:
            return Direction::Right;
        case Direction::Right:
            return Direction::Down;
        case Direction::Down:
            return Direction::Left;
        case Direction::Left:
            return Direction::Up;
    }
    // This should never be reached, but added to satisfy compiler
    return direction;
}