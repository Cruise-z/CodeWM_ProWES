#include "Board.h"

Board::Board() noexcept {
  clear();
}

void Board::clear() noexcept {
  for (auto& row : grid_) {
    for (auto& cell : row) {
      cell = 0;
    }
  }
}

std::uint16_t Board::at(std::size_t r, std::size_t c) const noexcept {
  return grid_[r][c];
}

void Board::set(std::size_t r, std::size_t c, std::uint16_t v) noexcept {
  grid_[r][c] = v;
}

void Board::getRow(std::size_t r, std::array<std::uint16_t, 4>& out) const noexcept {
  for (std::size_t i = 0; i < 4; ++i) {
    out[i] = grid_[r][i];
  }
}

void Board::setRow(std::size_t r, const std::array<std::uint16_t, 4>& in) noexcept {
  for (std::size_t i = 0; i < 4; ++i) {
    grid_[r][i] = in[i];
  }
}

void Board::getCol(std::size_t c, std::array<std::uint16_t, 4>& out) const noexcept {
  for (std::size_t i = 0; i < 4; ++i) {
    out[i] = grid_[i][c];
  }
}

void Board::setCol(std::size_t c, const std::array<std::uint16_t, 4>& in) noexcept {
  for (std::size_t i = 0; i < 4; ++i) {
    grid_[i][c] = in[i];
  }
}

bool Board::isFull() const noexcept {
  for (const auto& row : grid_) {
    for (const auto& cell : row) {
      if (cell == 0) {
        return false;
      }
    }
  }
  return true;
}

bool Board::hasEmpty() const noexcept {
  return !isFull();
}

std::uint16_t Board::maxTile() const noexcept {
  std::uint16_t max = 0;
  for (const auto& row : grid_) {
    for (const auto& cell : row) {
      if (cell > max) {
        max = cell;
      }
    }
  }
  return max;
}

std::size_t Board::side() noexcept {
  return 4;
}