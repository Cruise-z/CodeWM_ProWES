#ifndef ENTITIES_H
#define ENTITIES_H

#include <vector>
#include "Geometry.h"

/**
 * @brief Represents an obstacle in the arena.
 */
struct Obstacle {
    Point pos;

    /**
     * @brief Constructs an obstacle at the given position.
     * @param pos Position of the obstacle
     */
    explicit Obstacle(const Point& pos) : pos(pos) {}
};

/**
 * @brief Represents the game arena with boundaries and obstacles.
 */
class Arena {
private:
    Size size_;
    std::vector<Obstacle> obstacles_;

public:
    /**
     * @brief Constructs an arena with given dimensions.
     * @param width Width of the arena
     * @param height Height of the arena
     */
    Arena(int width, int height) : size_(width, height) {}

    /**
     * @brief Checks if a point is within the bounds of the arena.
     * @param point The point to check
     * @return True if point is within bounds, false otherwise
     */
    bool inBounds(const Point& point) const;

    /**
     * @brief Checks if a point contains an obstacle.
     * @param point The point to check
     * @return True if point contains an obstacle, false otherwise
     */
    bool isObstacle(const Point& point) const;

    /**
     * @brief Clears all obstacles from the arena.
     */
    void clearObstacles();

    /**
     * @brief Adds an obstacle to the arena.
     * @param pos Position where to add the obstacle
     * @return True if obstacle was added successfully, false otherwise
     */
    bool addObstacle(const Point& pos);
};

/**
 * @brief Represents a tank in the game.
 */
class Tank {
public:
    int id;
    Point pos;
    Direction dir;
    int health;
    bool alive;

    /**
     * @brief Constructs a tank with given parameters.
     * @param id Unique identifier for the tank
     * @param pos Initial position of the tank
     * @param dir Initial direction of the tank
     * @param health Initial health of the tank
     */
    Tank(int id, const Point& pos, Direction dir, int health);

    /**
     * @brief Rotates the tank 90 degrees to the left.
     */
    void rotateLeft();

    /**
     * @brief Rotates the tank 90 degrees to the right.
     */
    void rotateRight();
};

/**
 * @brief Represents a projectile in the game.
 */
class Projectile {
public:
    int ownerId;
    Point pos;
    Direction dir;
    bool alive;

    /**
     * @brief Constructs a projectile with given parameters.
     * @param ownerId ID of the tank that fired this projectile
     * @param pos Initial position of the projectile
     * @param dir Initial direction of the projectile
     */
    Projectile(int ownerId, const Point& pos, Direction dir);

    /**
     * @brief Moves the projectile one step forward.
     */
    void step();
};

/**
 * @brief Enum representing possible commands for tanks.
 */
enum class Command {
    None,
    Move,
    RotateLeft,
    RotateRight,
    Fire
};

#endif // ENTITIES_H