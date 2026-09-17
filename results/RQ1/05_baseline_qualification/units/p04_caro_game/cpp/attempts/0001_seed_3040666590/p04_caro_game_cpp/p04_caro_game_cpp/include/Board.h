#ifndef FIVEROW_BOARD_H
#define FIVEROW_BOARD_H

#include <vector>
#include "Common.h"

namespace fiverow {

/**
 * @brief Represents the game board with dimensions and cells
 */
class Board {
private:
    size_t width_;
    size_t height_;
    std::vector<CellState> cells_;

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
     * @param r Row index
     * @param c Column index
     * @return true if coordinates are valid, false otherwise
     */
    bool inBounds(size_t r, size_t c) const noexcept;

    /**
     * @brief Get the state of a cell at given coordinates
     * @pre inBounds(r, c) is true
     * @param r Row index
     * @param c Column index
     * @return CellState Current state of the cell
     */
    CellState get(size_t r, size_t c) const;

    /**
     * @brief Set the state of a cell at given coordinates
     * @param r Row index
     * @param c Column index
     * @param s New state to set
     * @return true if cell was successfully set, false if out of bounds
     */
    bool set(size_t r, size_t c, CellState s);

    /**
     * @brief Check if the board is completely filled
     * @return true if all cells are occupied, false otherwise
     */
    bool isFull() const noexcept;

    /**
     * @brief Clear the board, setting all cells to Empty
     */
    void clear();
};

}  // namespace fiverow

#endif // FIVEROW_BOARD_H