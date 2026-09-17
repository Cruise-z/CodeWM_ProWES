#ifndef BOARD_H
#define BOARD_H

#include <vector>
#include "Common.h"

namespace FiveInARow {

/**
 * @brief Represents the game board with dimensions and cells
 */
class Board {
private:
    size_t width;
    size_t height;
    std::vector<CellState> cells;

public:
    /**
     * @brief Construct a new Board object
     * @param w Width of the board (default: 15)
     * @param h Height of the board (default: 15)
     */
    explicit Board(size_t w = 15, size_t h = 15);

    /**
     * @brief Get the width of the board
     * @return size_t Width of the board
     */
    size_t getWidth() const noexcept;

    /**
     * @brief Get the height of the board
     * @return size_t Height of the board
     */
    size_t getHeight() const noexcept;

    /**
     * @brief Check if given coordinates are within board bounds
     * @param r Row coordinate
     * @param c Column coordinate
     * @return bool True if coordinates are valid, false otherwise
     */
    bool inBounds(size_t r, size_t c) const noexcept;

    /**
     * @brief Get the state of a cell at given coordinates
     * @pre inBounds(r, c) must be true
     * @param r Row coordinate
     * @param c Column coordinate
     * @return CellState State of the cell at (r, c)
     */
    CellState get(size_t r, size_t c) const;

    /**
     * @brief Set the state of a cell at given coordinates
     * @param r Row coordinate
     * @param c Column coordinate
     * @param s State to set the cell to
     * @return bool True if cell was successfully set, false if out-of-bounds
     */
    bool set(size_t r, size_t c, CellState s);

    /**
     * @brief Check if the board is completely filled
     * @return bool True if board is full, false otherwise
     */
    bool isFull() const noexcept;

    /**
     * @brief Clear the board by setting all cells to empty
     */
    void clear();
};

} // namespace FiveInARow

#endif // BOARD_H