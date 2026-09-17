#include "Board.h"
#include <stdexcept>

namespace gomoku {

Board::Board(size_t w, size_t h) : width(w), height(h) {
    if (width == 0 || height == 0) {
        throw std::invalid_argument("Board dimensions must be positive");
    }
    cells.resize(width * height, CellState::Empty);
}

size_t Board::getWidth() const noexcept {
    return width;
}

size_t Board::getHeight() const noexcept {
    return height;
}

bool Board::inBounds(size_t r, size_t c) const noexcept {
    return r < height && c < width;
}

CellState Board::get(size_t r, size_t c) const {
    if (!inBounds(r, c)) {
        throw std::out_of_range("Coordinates out of bounds");
    }
    return cells[r * width + c];
}

bool Board::set(size_t r, size_t c, CellState s) {
    if (!inBounds(r, c)) {
        return false;
    }
    cells[r * width + c] = s;
    return true;
}

bool Board::isFull() const noexcept {
    for (const auto& cell : cells) {
        if (cell == CellState::Empty) {
            return false;
        }
    }
    return true;
}

void Board::clear() {
    for (auto& cell : cells) {
        cell = CellState::Empty;
    }
}

}  // namespace gomoku