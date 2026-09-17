#ifndef GEOMETRY_H
#define GEOMETRY_H

#include <cstdint>

// Forward declarations
struct Point;
struct Size;
enum class Direction : int8_t;

/**
 * @brief Geometry utilities for grid-based movement and direction handling
 */
class Geometry {
public:
    /**
     * @brief Check if a point is within the bounds of a given size
     * @param point The point to check
     * @param size The size representing the bounds
     * @return true if point is within bounds, false otherwise
     */
    static bool inBounds(Point point, Size size);

    /**
     * @brief Advance a point in a given direction
     * @param point The starting point
     * @param direction The direction to advance
     * @return The new point after advancement
     */
    static Point advance(Point point, Direction direction);

    /**
     * @brief Rotate a direction 90 degrees to the left
     * @param direction The original direction
     * @return The rotated direction
     */
    static Direction rotateLeft(Direction direction);

    /**
     * @brief Rotate a direction 90 degrees to the right
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
     * @brief Construct a new Point object
     * @param x The x coordinate
     * @param y The y coordinate
     */
    Point(int32_t x, int32_t y) : x(x), y(y) {}

    /**
     * @brief Compare two points for ordering
     * @param other The other point to compare against
     * @return true if this point is less than the other point
     */
    bool operator<(const Point& other) const {
        if (y != other.y) {
            return y < other.y;
        }
        return x < other.x;
    }
};

/**
 * @brief Represents the dimensions of a rectangle
 */
struct Size {
    int32_t width;
    int32_t height;

    /**
     * @brief Construct a new Size object
     * @param width The width
     * @param height The height
     */
    Size(int32_t width, int32_t height) : width(width), height(height) {}
};

/**
 * @brief Enumeration of possible directions in the grid
 */
enum class Direction : int8_t {
    Up = 0,
    Right = 1,
    Down = 2,
    Left = 3
};

#endif // GEOMETRY_H