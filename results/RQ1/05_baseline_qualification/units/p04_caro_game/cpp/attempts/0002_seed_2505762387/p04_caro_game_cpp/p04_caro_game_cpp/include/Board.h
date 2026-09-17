#ifndef GOMOKU_BOARD_H
#define GOMOKU_BOARD_H

#include <vector>
#include "Common.h"

namespace gomoku {

/**
 * @brief Represents the game board for Gomoku
 * 
 * The board is a grid of cells that can be in one of three states:
 * Empty, X (Player X), or O (Player O).
 */
class Board {
private:
    size_t width_;      ///< Width of the board
    size_t height_;     ///< Height of the board
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
     * @return true If coordinates are valid
     * @return false If coordinates are out of bounds
     */
    bool inBounds(size_t r, size_t c) const noexcept;

    /**
     * @brief Get the state of a cell at given coordinates
     * 
     * @pre inBounds(r, c) must be true
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
     * @return true If the operation was successful
     * @return false If coordinates were out of bounds
     */
    bool set(size_t r, size_t c, CellState s);

    /**
     * @brief Check if the board is completely filled
     * 
     * @return true If all cells are occupied
     * @return false If there are empty cells
     */
    bool isFull() const noexcept;

    /**
     * @brief Clear the board, setting all cells to Empty
     */
    void clear();
};

}  // namespace gomoku

#endif // GOMOKU_BOARD_H