#ifndef ENTITIES_H
#define ENTITIES_H

#include <vector>
#include "Geometry.h"

/**
 * @brief Represents an obstacle in the arena
 */
struct Obstacle {
    Point pos;

    /**
     * @brief Construct a new Obstacle object
     * @param pos The position of the obstacle
     */
    explicit Obstacle(Point pos) : pos(pos) {}
};

/**
 * @brief Represents the game arena with boundaries and obstacles
 */
class Arena {
private:
    Size size_;
    std::vector<Obstacle> obstacles_;

public:
    /**
     * @brief Construct a new Arena object
     * @param width The width of the arena
     * @param height The height of the arena
     */
    Arena(int width, int height) : size_(width, height) {}

    /**
     * @brief Check if a point is within the bounds of the arena
     * @param point The point to check
     * @return true if point is within bounds, false otherwise
     */
    bool inBounds(Point point) const {
        return Geometry::inBounds(point, size_);
    }

    /**
     * @brief Check if a point contains an obstacle
     * @param point The point to check
     * @return true if point contains an obstacle, false otherwise
     */
    bool isObstacle(Point point) const {
        for (const auto& obstacle : obstacles_) {
            if (obstacle.pos == point) {
                return true;
            }
        }
        return false;
    }

    /**
     * @brief Clear all obstacles from the arena
     */
    void clearObstacles() {
        obstacles_.clear();
    }

    /**
     * @brief Add an obstacle to the arena
     * @param pos The position to add the obstacle
     * @return true if obstacle was added, false if position is invalid or occupied
     */
    bool addObstacle(Point pos) {
        if (!inBounds(pos) || isObstacle(pos)) {
            return false;
        }
        obstacles_.emplace_back(pos);
        return true;
    }

    /**
     * @brief Get the size of the arena
     * @return The size of the arena
     */
    const Size& size() const {
        return size_;
    }

    /**
     * @brief Get the list of obstacles
     * @return Vector of obstacles
     */
    const std::vector<Obstacle>& obstacles() const {
        return obstacles_;
    }
};

/**
 * @brief Represents a tank in the game
 */
class Tank {
private:
    int id_;
    Point pos_;
    Direction dir_;
    int health_;
    bool alive_;

public:
    /**
     * @brief Construct a new Tank object
     * @param id The unique identifier of the tank
     * @param pos The initial position of the tank
     * @param dir The initial direction of the tank
     * @param health The initial health of the tank
     */
    Tank(int id, Point pos, Direction dir, int health = 3)
        : id_(id), pos_(pos), dir_(dir), health_(health), alive_(true) {}

    /**
     * @brief Rotate the tank 90 degrees to the left
     */
    void rotateLeft() {
        dir_ = Geometry::rotateLeft(dir_);
    }

    /**
     * @brief Rotate the tank 90 degrees to the right
     */
    void rotateRight() {
        dir_ = Geometry::rotateRight(dir_);
    }

    /**
     * @brief Move the tank one step forward in its current direction
     * @param arena The arena to check for boundaries and obstacles
     * @return true if the tank moved successfully, false if movement was blocked
     */
    bool move(const Arena& arena) {
        Point newPos = Geometry::advance(pos_, dir_);
        if (arena.inBounds(newPos) && !arena.isObstacle(newPos)) {
            pos_ = newPos;
            return true;
        }
        return false;
    }

    /**
     * @brief Get the tank's ID
     * @return The tank's ID
     */
    int id() const {
        return id_;
    }

    /**
     * @brief Get the tank's position
     * @return The tank's position
     */
    const Point& pos() const {
        return pos_;
    }

    /**
     * @brief Get the tank's direction
     * @return The tank's direction
     */
    Direction dir() const {
        return dir_;
    }

    /**
     * @brief Get the tank's health
     * @return The tank's health
     */
    int health() const {
        return health_;
    }

    /**
     * @brief Get whether the tank is alive
     * @return true if the tank is alive, false otherwise
     */
    bool alive() const {
        return alive_;
    }

    /**
     * @brief Reduce the tank's health by one point
     */
    void damage() {
        health_--;
        if (health_ <= 0) {
            alive_ = false;
        }
    }

    /**
     * @brief Reset the tank to its initial state
     * @param pos The initial position of the tank
     * @param dir The initial direction of the tank
     * @param health The initial health of the tank
     */
    void reset(Point pos, Direction dir, int health = 3) {
        pos_ = pos;
        dir_ = dir;
        health_ = health;
        alive_ = true;
    }
};

/**
 * @brief Represents a projectile in the game
 */
class Projectile {
private:
    int ownerId_;
    Point pos_;
    Direction dir_;
    bool alive_;

public:
    /**
     * @brief Construct a new Projectile object
     * @param ownerId The ID of the tank that fired this projectile
     * @param pos The initial position of the projectile
     * @param dir The direction the projectile is moving
     */
    Projectile(int ownerId, Point pos, Direction dir)
        : ownerId_(ownerId), pos_(pos), dir_(dir), alive_(true) {}

    /**
     * @brief Move the projectile one step forward
     */
    void step() {
        if (alive_) {
            pos_ = Geometry::advance(pos_, dir_);
        }
    }

    /**
     * @brief Get the owner ID of the projectile
     * @return The owner ID
     */
    int ownerId() const {
        return ownerId_;
    }

    /**
     * @brief Get the position of the projectile
     * @return The position
     */
    const Point& pos() const {
        return pos_;
    }

    /**
     * @brief Get the direction of the projectile
     * @return The direction
     */
    Direction dir() const {
        return dir_;
    }

    /**
     * @brief Check if the projectile is alive
     * @return true if the projectile is alive, false otherwise
     */
    bool alive() const {
        return alive_;
    }

    /**
     * @brief Mark the projectile as dead
     */
    void kill() {
        alive_ = false;
    }

    /**
     * @brief Reset the projectile to its initial state
     * @param ownerId The ID of the tank that fired this projectile
     * @param pos The initial position of the projectile
     * @param dir The direction the projectile is moving
     */
    void reset(int ownerId, Point pos, Direction dir) {
        ownerId_ = ownerId;
        pos_ = pos;
        dir_ = dir;
        alive_ = true;
    }
};

/**
 * @brief Enumeration of possible commands for controlling tanks
 */
enum class Command {
    None,
    Move,
    RotateLeft,
    RotateRight,
    Fire
};

#endif // ENTITIES_H