#ifndef GEOMETRY_H
#define GEOMETRY_H

#include <cstdint>

// Forward declarations
struct Point;
struct Size;
enum class Direction : int8_t;

/**
 * @brief Geometric utilities for grid-based game operations
 */
class Geometry {
public:
    /**
     * @brief Checks if a point is within the bounds of a given size
     * @param point The point to check
     * @param size The bounding size
     * @return True if point is within bounds, false otherwise
     */
    static bool inBounds(Point point, Size size);

    /**
     * @brief Advances a point in a given direction
     * @param point The starting point
     * @param direction The direction to move
     * @return The new point after advancement
     */
    static Point advance(Point point, Direction direction);

    /**
     * @brief Rotates a direction 90 degrees to the left
     * @param direction The original direction
     * @return The rotated direction
     */
    static Direction rotateLeft(Direction direction);

    /**
     * @brief Rotates a direction 90 degrees to the right
     * @param direction The original direction
     * @return The rotated direction
     */
    static Direction rotateRight(Direction direction);
};

/**
 * @brief Represents a point in 2D space
 */
struct Point {
    int32_t x;
    int32_t y;

    /**
     * @brief Constructs a point with given coordinates
     * @param x X coordinate
     * @param y Y coordinate
     */
    Point(int32_t x, int32_t y) : x(x), y(y) {}

    /**
     * @brief Less than operator for sorting points
     * @param other Another point to compare with
     * @return True if this point is less than the other point
     */
    bool operator<(const Point& other) const {
        return (x < other.x) || (x == other.x && y < other.y);
    }
};

/**
 * @brief Represents the dimensions of a rectangle
 */
struct Size {
    int32_t width;
    int32_t height;

    /**
     * @brief Constructs a size with given dimensions
     * @param width Width dimension
     * @param height Height dimension
     */
    Size(int32_t width, int32_t height) : width(width), height(height) {}
};

/**
 * @brief Enum representing compass directions
 */
enum class Direction : int8_t {
    Up = 0,
    Right = 1,
    Down = 2,
    Left = 3
};

#endif // GEOMETRY_H