#ifndef SNAKE_SNAKE_H_
#define SNAKE_SNAKE_H_

#include "Types.h"
#include <cstddef>
#include <deque>

namespace snake {

/// Represents the snake in the game, including its body, direction, and movement logic
class Snake {
 public:
  /// Constructs a new Snake with the specified starting position, direction, and initial length
  /// @param start The starting position of the snake's head
  /// @param dir The initial direction of the snake
  /// @param initialLength The initial length of the snake (must be positive)
  Snake(Position start, Direction dir, int initialLength);

  /// Gets the position of the snake's head
  /// @return The position of the snake's head
  Position head() const;

  /// Gets the position of the snake's tail
  /// @return The position of the snake's tail
  Position tail() const;

  /// Gets the snake's body segments
  /// @return A const reference to the deque of body positions
  const std::deque<Position>& body() const noexcept;

  /// Gets the current direction of the snake
  /// @return The current direction of the snake
  Direction direction() const noexcept;

  /// Attempts to change the snake's direction
  /// @param d The desired new direction
  /// @return true if the direction was successfully changed, false if the change was ignored (e.g., 180-degree turn)
  bool trySetDirection(Direction d);

  /// Moves the snake to a new position
  /// @param next The new position for the snake's head
  /// @param grow If true, the snake grows by one segment; if false, the tail is removed
  void advanceTo(Position next, bool grow);

  /// Checks if any segment of the snake occupies a given position
  /// @param p The position to check
  /// @return true if any segment of the snake occupies the position, false otherwise
  bool occupies(Position p) const noexcept;

 private:
  std::deque<Position> body_;
  Direction dir_;
};

}  // namespace snake

#endif  // SNAKE_SNAKE_H_