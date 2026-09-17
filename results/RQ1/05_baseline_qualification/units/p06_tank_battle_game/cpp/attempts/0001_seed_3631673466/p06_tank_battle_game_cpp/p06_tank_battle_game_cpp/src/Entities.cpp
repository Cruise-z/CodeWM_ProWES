#include "Entities.h"

bool Arena::inBounds(Point point) const {
    return Geometry::inBounds(point, size_);
}

bool Arena::isObstacle(Point point) const {
    for (const auto& obstacle : obstacles_) {
        if (obstacle.pos == point) {
            return true;
        }
    }
    return false;
}

void Arena::clearObstacles() {
    obstacles_.clear();
}

bool Arena::addObstacle(Point pos) {
    if (!inBounds(pos) || isObstacle(pos)) {
        return false;
    }
    obstacles_.emplace_back(pos);
    return true;
}

const Size& Arena::size() const {
    return size_;
}

const std::vector<Obstacle>& Arena::obstacles() const {
    return obstacles_;
}

void Tank::rotateLeft() {
    dir_ = Geometry::rotateLeft(dir_);
}

void Tank::rotateRight() {
    dir_ = Geometry::rotateRight(dir_);
}

bool Tank::move(const Arena& arena) {
    Point newPos = Geometry::advance(pos_, dir_);
    if (arena.inBounds(newPos) && !arena.isObstacle(newPos)) {
        pos_ = newPos;
        return true;
    }
    return false;
}

int Tank::id() const {
    return id_;
}

const Point& Tank::pos() const {
    return pos_;
}

Direction Tank::dir() const {
    return dir_;
}

int Tank::health() const {
    return health_;
}

bool Tank::alive() const {
    return alive_;
}

void Tank::damage() {
    health_--;
    if (health_ <= 0) {
        alive_ = false;
    }
}

void Tank::reset(Point pos, Direction dir, int health) {
    pos_ = pos;
    dir_ = dir;
    health_ = health;
    alive_ = true;
}

void Projectile::step() {
    if (alive_) {
        pos_ = Geometry::advance(pos_, dir_);
    }
}

int Projectile::ownerId() const {
    return ownerId_;
}

const Point& Projectile::pos() const {
    return pos_;
}

Direction Projectile::dir() const {
    return dir_;
}

bool Projectile::alive() const {
    return alive_;
}

void Projectile::kill() {
    alive_ = false;
}

void Projectile::reset(int ownerId, Point pos, Direction dir) {
    ownerId_ = ownerId;
    pos_ = pos;
    dir_ = dir;
    alive_ = true;
}