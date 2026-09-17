#ifndef SNAKE_TYPES_H_
#define SNAKE_TYPES_H_

namespace snake {

/// Represents a position on the game grid
struct Position {
  int x;
  int y;
};

/// Represents the four possible directions of movement
enum class Direction {
  Up,
  Down,
  Left,
  Right
};

}  // namespace snake

#endif  // SNAKE_TYPES_H_