#ifndef BOARD_H
#define BOARD_H

#include <vector>
#include "Common.h"

namespace FiveInARow {

/**
 * @brief Represents the game board for a Five in a Row game
 */
class Board {
private:
    size_t width_;
    size_t height_;
    std::vector<CellState> cells_;

public:
    /**
     * @brief Constructs a new Board object
     * @param w Width of the board (default: 15)
     * @param h Height of the board (default: 15)
     */
    explicit Board(size_t w = 15, size_t h = 15);

    /**
     * @brief Gets the width of the board
     * @return Width of the board
     */
    size_t getWidth() const noexcept;

    /**
     * @brief Gets the height of the board
     * @return Height of the board
     */
    size_t getHeight() const noexcept;

    /**
     * @brief Checks if given coordinates are within board boundaries
     * @param r Row index
     * @param c Column index
     * @return True if coordinates are valid, false otherwise
     */
    bool inBounds(size_t r, size_t c) const noexcept;

    /**
     * @brief Gets the state of a cell at given coordinates
     * @pre inBounds(r, c) must be true
     * @param r Row index
     * @param c Column index
     * @return State of the cell at (r, c)
     */
    CellState get(size_t r, size_t c) const;

    /**
     * @brief Sets the state of a cell at given coordinates
     * @param r Row index
     * @param c Column index
     * @param s New state for the cell
     * @return True if the operation was successful, false if out-of-bounds
     */
    bool set(size_t r, size_t c, CellState s);

    /**
     * @brief Checks if the board is completely filled
     * @return True if all cells are occupied, false otherwise
     */
    bool isFull() const noexcept;

    /**
     * @brief Clears the board, setting all cells to empty
     */
    void clear();
};

}  // namespace FiveInARow

#endif // BOARD_H