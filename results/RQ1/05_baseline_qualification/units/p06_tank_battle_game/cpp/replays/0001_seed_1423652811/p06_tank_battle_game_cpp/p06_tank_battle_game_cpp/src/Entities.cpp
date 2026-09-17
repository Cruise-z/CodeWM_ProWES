#include "Entities.h"
#include "Geometry.h"

// Implementation of Arena methods
bool Arena::inBounds(const Point& point) const {
    return Geometry::inBounds(point, size_);
}

bool Arena::isObstacle(const Point& point) const {
    for (const auto& obstacle : obstacles_) {
        if (obstacle.pos.x == point.x && obstacle.pos.y == point.y) {
            return true;
        }
    }
    return false;
}

void Arena::clearObstacles() {
    obstacles_.clear();
}

bool Arena::addObstacle(const Point& pos) {
    // Check if position is within bounds
    if (!inBounds(pos)) {
        return false;
    }
    
    // Check if position already has an obstacle
    if (isObstacle(pos)) {
        return false;
    }
    
    obstacles_.emplace_back(pos);
    return true;
}

// Implementation of Tank methods
Tank::Tank(int id, const Point& pos, Direction dir, int health) 
    : id(id), pos(pos), dir(dir), health(health), alive(true) {}

void Tank::rotateLeft() {
    dir = Geometry::rotateLeft(dir);
}

void Tank::rotateRight() {
    dir = Geometry::rotateRight(dir);
}

// Implementation of Projectile methods
Projectile::Projectile(int ownerId, const Point& pos, Direction dir) 
    : ownerId(ownerId), pos(pos), dir(dir), alive(true) {}

void Projectile::step() {
    if (!alive) {
        return;
    }
    
    pos = Geometry::advance(pos, dir);
}