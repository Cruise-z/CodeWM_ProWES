#include "Board.h"

namespace snake {

Board::Board(std::size_t width, std::size_t height) : width_(width), height_(height) {}

std::size_t Board::getWidth() const noexcept {
  return width_;
}

std::size_t Board::getHeight() const noexcept {
  return height_;
}

bool Board::inBounds(Position p) const noexcept {
  return p.x >= 0 && p.x < static_cast<int>(width_) && 
         p.y >= 0 && p.y < static_cast<int>(height_);
}

}  // namespace snake