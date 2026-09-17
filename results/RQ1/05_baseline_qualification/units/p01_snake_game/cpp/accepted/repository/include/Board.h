#ifndef SNAKE_BOARD_H_
#define SNAKE_BOARD_H_

#include "Types.h"
#include <cstddef>

namespace snake {

/// Represents the game board with dimensions and bounds checking
class Board {
 public:
  /// Constructs a new Board with the specified width and height
  /// @param width The width of the board (must be > 0)
  /// @param height The height of the board (must be > 0)
  Board(std::size_t width, std::size_t height);

  /// Gets the width of the board
  /// @return The width of the board
  std::size_t getWidth() const noexcept;

  /// Gets the height of the board
  /// @return The height of the board
  std::size_t getHeight() const noexcept;

  /// Checks if a position is within the bounds of the board
  /// @param p The position to check
  /// @return true if the position is within the board's bounds, false otherwise
  bool inBounds(Position p) const noexcept;

 private:
  std::size_t width_;
  std::size_t height_;
};

}  // namespace snake

#endif  // SNAKE_BOARD_H_