#ifndef ENTITIES_H
#define ENTITIES_H

#include <vector>
#include "Geometry.h"

/**
 * @brief Represents an obstacle in the game arena
 */
struct Obstacle {
    Point pos;

    /**
     * @brief Constructs an obstacle at the given position
     * @param pos The position of the obstacle
     */
    explicit Obstacle(Point pos) : pos(pos) {}
};

/**
 * @brief Represents the game arena with boundaries and obstacles
 */
class Arena {
public:
    Size size;
    std::vector<Obstacle> obstacles;

    /**
     * @brief Constructs an arena with given dimensions
     * @param width The width of the arena
     * @param height The height of the arena
     */
    Arena(int32_t width, int32_t height) : size(width, height) {}

    /**
     * @brief Checks if a point is within the bounds of the arena
     * @param point The point to check
     * @return True if the point is within bounds, false otherwise
     */
    bool inBounds(Point point) const {
        return Geometry::inBounds(point, size);
    }

    /**
     * @brief Checks if a point contains an obstacle
     * @param point The point to check
     * @return True if there is an obstacle at the point, false otherwise
     */
    bool isObstacle(Point point) const {
        for (const auto& obstacle : obstacles) {
            if (obstacle.pos.x == point.x && obstacle.pos.y == point.y) {
                return true;
            }
        }
        return false;
    }

    /**
     * @brief Clears all obstacles from the arena
     */
    void clearObstacles() {
        obstacles.clear();
    }

    /**
     * @brief Adds an obstacle at the given position if it's within bounds and not occupied
     * @param pos The position to add the obstacle
     * @return True if the obstacle was added successfully, false otherwise
     */
    bool addObstacle(Point pos) {
        if (!inBounds(pos)) {
            return false;
        }
        
        if (isObstacle(pos)) {
            return false;
        }
        
        obstacles.emplace_back(pos);
        return true;
    }
};

/**
 * @brief Represents a tank in the game
 */
class Tank {
public:
    int32_t id;
    Point pos;
    Direction dir;
    int32_t health;
    bool alive;

    /**
     * @brief Constructs a tank with given parameters
     * @param id The unique identifier of the tank
     * @param pos The initial position of the tank
     * @param dir The initial direction of the tank
     * @param health The initial health of the tank
     */
    Tank(int32_t id, Point pos, Direction dir, int32_t health = 3)
        : id(id), pos(pos), dir(dir), health(health), alive(true) {}

    /**
     * @brief Rotates the tank 90 degrees to the left
     */
    void rotateLeft() {
        dir = Geometry::rotateLeft(dir);
    }

    /**
     * @brief Rotates the tank 90 degrees to the right
     */
    void rotateRight() {
        dir = Geometry::rotateRight(dir);
    }
};

/**
 * @brief Represents a projectile in the game
 */
class Projectile {
public:
    int32_t ownerId;
    Point pos;
    Direction dir;
    bool alive;

    /**
     * @brief Constructs a projectile with given parameters
     * @param ownerId The ID of the tank that fired this projectile
     * @param pos The initial position of the projectile
     * @param dir The direction the projectile is moving
     */
    Projectile(int32_t ownerId, Point pos, Direction dir)
        : ownerId(ownerId), pos(pos), dir(dir), alive(true) {}

    /**
     * @brief Moves the projectile one step in its current direction
     */
    void step() {
        pos = Geometry::advance(pos, dir);
    }
};

/**
 * @brief Enumeration of possible commands
 */
enum class Command {
    None,
    Move,
    RotateLeft,
    RotateRight,
    Fire
};

#endif // ENTITIES_H