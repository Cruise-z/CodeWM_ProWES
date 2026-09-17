#ifndef BOARD_H
#define BOARD_H

#include <array>
#include <cstdint>
#include <cstddef>

/**
 * @brief Represents a 4x4 game board for 2048.
 */
class Board {
 public:
  /**
   * @brief Constructs a new Board object.
   */
  Board() noexcept;

  /**
   * @brief Clears the board, setting all cells to 0 (empty).
   */
  void clear() noexcept;

  /**
   * @brief Gets the value at the specified position.
   * @param r Row index (0-3).
   * @param c Column index (0-3).
   * @return Value at (r, c).
   */
  std::uint16_t at(std::size_t r, std::size_t c) const noexcept;

  /**
   * @brief Sets the value at the specified position.
   * @param r Row index (0-3).
   * @param c Column index (0-3).
   * @param v Value to set.
   */
  void set(std::size_t r, std::size_t c, std::uint16_t v) noexcept;

  /**
   * @brief Gets a row from the board.
   * @param r Row index (0-3).
   * @param out Output array to store the row.
   */
  void getRow(std::size_t r, std::array<std::uint16_t, 4>& out) const noexcept;

  /**
   * @brief Sets a row on the board.
   * @param r Row index (0-3).
   * @param in Input array containing the row data.
   */
  void setRow(std::size_t r, const std::array<std::uint16_t, 4>& in) noexcept;

  /**
   * @brief Gets a column from the board.
   * @param c Column index (0-3).
   * @param out Output array to store the column.
   */
  void getCol(std::size_t c, std::array<std::uint16_t, 4>& out) const noexcept;

  /**
   * @brief Sets a column on the board.
   * @param c Column index (0-3).
   * @param in Input array containing the column data.
   */
  void setCol(std::size_t c, const std::array<std::uint16_t, 4>& in) noexcept;

  /**
   * @brief Checks if the board is completely filled.
   * @return True if all cells are occupied, false otherwise.
   */
  bool isFull() const noexcept;

  /**
   * @brief Checks if the board has any empty cells.
   * @return True if at least one cell is empty, false otherwise.
   */
  bool hasEmpty() const noexcept;

  /**
   * @brief Gets the maximum tile value on the board.
   * @return Maximum tile value, or 0 if the board is empty.
   */
  std::uint16_t maxTile() const noexcept;

  /**
   * @brief Gets the side length of the board.
   * @return Side length (4 for a 4x4 board).
   */
  static std::size_t side() noexcept;

 private:
  std::array<std::array<std::uint16_t, 4>, 4> grid_;
};

#endif // BOARD_H