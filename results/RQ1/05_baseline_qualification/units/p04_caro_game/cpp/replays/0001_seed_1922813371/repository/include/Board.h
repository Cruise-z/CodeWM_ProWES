#ifndef GOMOKU_BOARD_H
#define GOMOKU_BOARD_H

#include <cstddef>
#include <vector>
#include "Common.h"

namespace gomoku {

/**
 * @brief Represents the game board for Gomoku
 * 
 * The Board class manages a grid of cells where players place their stones.
 * It provides methods for accessing and modifying cell states, checking
 * boundaries, and determining if the board is full.
 */
class Board {
private:
    size_t width_;     ///< Width of the board
    size_t height_;    ///< Height of the board
    std::vector<CellState> cells_;  ///< Storage for all cells in row-major order

public:
    /**
     * @brief Construct a new Board object
     * 
     * @param w Width of the board (default: 15)
     * @param h Height of the board (default: 15)
     */
    explicit Board(size_t w = 15, size_t h = 15);

    /**
     * @brief Get the width of the board
     * 
     * @return size_t Width of the board
     */
    size_t getWidth() const noexcept;

    /**
     * @brief Get the height of the board
     * 
     * @return size_t Height of the board
     */
    size_t getHeight() const noexcept;

    /**
     * @brief Check if given coordinates are within board boundaries
     * 
     * @param r Row index
     * @param c Column index
     * @return true if coordinates are valid
     * @return false if coordinates are outside the board
     */
    bool inBounds(size_t r, size_t c) const noexcept;

    /**
     * @brief Get the state of a cell at given coordinates
     * 
     * @pre inBounds(r, c) is true
     * @param r Row index
     * @param c Column index
     * @return CellState State of the cell at (r, c)
     */
    CellState get(size_t r, size_t c) const;

    /**
     * @brief Set the state of a cell at given coordinates
     * 
     * @param r Row index
     * @param c Column index
     * @param s New state to set
     * @return true if cell was successfully set
     * @return false if coordinates were out of bounds
     */
    bool set(size_t r, size_t c, CellState s);

    /**
     * @brief Check if the board is completely filled
     * 
     * @return true if all cells are occupied
     * @return false if there are empty cells
     */
    bool isFull() const noexcept;

    /**
     * @brief Clear the board by setting all cells to empty
     */
    void clear();
};

} // namespace gomoku

#endif // GOMOKU_BOARD_H