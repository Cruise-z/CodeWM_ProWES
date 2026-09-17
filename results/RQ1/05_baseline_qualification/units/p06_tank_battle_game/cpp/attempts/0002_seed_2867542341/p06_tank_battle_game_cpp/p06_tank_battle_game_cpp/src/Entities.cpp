#include "Entities.h"

bool Arena::isObstacle(Point point) const {
    for (const auto& obstacle : obstacles) {
        if (obstacle.pos.x == point.x && obstacle.pos.y == point.y) {
            return true;
        }
    }
    return false;
}

void Tank::rotateLeft() {
    dir = Geometry::rotateLeft(dir);
}

void Tank::rotateRight() {
    dir = Geometry::rotateRight(dir);
}

void Projectile::step() {
    pos = Geometry::advance(pos, dir);
}