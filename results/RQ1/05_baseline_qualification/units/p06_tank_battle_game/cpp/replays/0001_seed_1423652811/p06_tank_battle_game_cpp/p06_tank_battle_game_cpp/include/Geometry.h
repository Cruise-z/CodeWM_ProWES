#ifndef GEOMETRY_H
#define GEOMETRY_H

#include <cstdint>

// Forward declarations
struct Point;
struct Size;

/**
 * @brief Enum representing directions in the grid.
 */
enum class Direction : int8_t {
    Up = 0,
    Right = 1,
    Down = 2,
    Left = 3
};

/**
 * @brief Represents a point in 2D space.
 */
struct Point {
    int32_t x;
    int32_t y;

    /**
     * @brief Constructs a Point with given coordinates.
     * @param x X coordinate
     * @param y Y coordinate
     */
    Point(int32_t x, int32_t y) : x(x), y(y) {}

    /**
     * @brief Comparison operator for sorting Points.
     * @param other Other Point to compare with
     * @return True if this Point is less than other Point
     */
    bool operator<(const Point& other) const {
        if (x != other.x) {
            return x < other.x;
        }
        return y < other.y;
    }
};

/**
 * @brief Represents the size of a rectangle.
 */
struct Size {
    int32_t width;
    int32_t height;

    /**
     * @brief Constructs a Size with given dimensions.
     * @param width Width dimension
     * @param height Height dimension
     */
    Size(int32_t width, int32_t height) : width(width), height(height) {}
};

/**
 * @brief Provides geometric utilities for grid-based operations.
 */
class Geometry {
public:
    /**
     * @brief Checks if a point is within the bounds of a size.
     * @param point The point to check
     * @param size The size defining the bounds
     * @return True if point is within bounds, false otherwise
     */
    static bool inBounds(const Point& point, const Size& size);

    /**
     * @brief Advances a point in the given direction.
     * @param point The starting point
     * @param direction The direction to advance
     * @return The new point after advancement
     */
    static Point advance(const Point& point, Direction direction);

    /**
     * @brief Rotates a direction 90 degrees to the left.
     * @param direction The direction to rotate
     * @return The rotated direction
     */
    static Direction rotateLeft(Direction direction);

    /**
     * @brief Rotates a direction 90 degrees to the right.
     * @param direction The direction to rotate
     * @return The rotated direction
     */
    static Direction rotateRight(Direction direction);
};

#endif // GEOMETRY_H