#include "Board.h"
#include <stdexcept>

namespace FiveInARow {

Board::Board(size_t w, size_t h) : width_(w), height_(h) {
    if (width_ == 0 || height_ == 0) {
        throw std::invalid_argument("Board dimensions must be positive");
    }
    cells_.assign(width_ * height_, CellState::Empty);
}

size_t Board::getWidth() const noexcept {
    return width_;
}

size_t Board::getHeight() const noexcept {
    return height_;
}

bool Board::inBounds(size_t r, size_t c) const noexcept {
    return r < height_ && c < width_;
}

CellState Board::get(size_t r, size_t c) const {
    if (!inBounds(r, c)) {
        throw std::out_of_range("Coordinates out of bounds");
    }
    return cells_[r * width_ + c];
}

bool Board::set(size_t r, size_t c, CellState s) {
    if (!inBounds(r, c)) {
        return false;
    }
    cells_[r * width_ + c] = s;
    return true;
}

bool Board::isFull() const noexcept {
    for (const auto& cell : cells_) {
        if (cell == CellState::Empty) {
            return false;
        }
    }
    return true;
}

void Board::clear() {
    cells_.assign(width_ * height_, CellState::Empty);
}

}  // namespace FiveInARow