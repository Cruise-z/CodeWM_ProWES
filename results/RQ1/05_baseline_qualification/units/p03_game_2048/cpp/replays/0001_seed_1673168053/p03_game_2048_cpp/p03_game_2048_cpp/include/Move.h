#ifndef MOVE_H
#define MOVE_H

#include <array>
#include <cstdint>
#include <cstddef>

class Board;

namespace Move {
  /**
   * @brief Direction enum for movement in the game.
   */
  enum class Direction {
    Left,
    Right,
    Up,
    Down
  };

  /**
   * @brief Result structure for line movement operations.
   */
  struct LineMoveResult {
    std::array<std::uint16_t, 4> line;
    bool moved;
    std::uint32_t scoreGained;
  };

  /**
   * @brief Result structure for board movement operations.
   */
  struct BoardMoveResult {
    bool moved;
    std::uint32_t scoreGained;
  };

  /**
   * @brief Processes a single line according to 2048 rules.
   * @param line Input line of 4 tiles.
   * @return Result of the line processing including the new line, whether it moved, and score gained.
   */
  LineMoveResult processLine(const std::array<std::uint16_t, 4>& line) noexcept;

  /**
   * @brief Applies a move in the specified direction to the board.
   * @param board Reference to the board to modify.
   * @param dir Direction of the move.
   * @return Result of the board move including whether anything moved and score gained.
   */
  BoardMoveResult applyMove(Board& board, Direction dir) noexcept;

  /**
   * @brief Checks if there are any legal moves remaining on the board.
   * @param board Reference to the board to check.
   * @return True if there is at least one legal move, false otherwise.
   */
  bool hasLegalMove(const Board& board) noexcept;
}  // namespace Move

#endif // MOVE_H