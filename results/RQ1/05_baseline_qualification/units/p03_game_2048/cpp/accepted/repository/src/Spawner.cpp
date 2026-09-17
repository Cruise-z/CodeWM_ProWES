#include "Spawner.h"
#include "Board.h"

bool Spawner::spawn(Board& board) noexcept {
  // Find the first empty cell in row-major order
  for (std::size_t r = 0; r < Board::side(); ++r) {
    for (std::size_t c = 0; c < Board::side(); ++c) {
      if (board.at(r, c) == 0) {
        board.set(r, c, 2);
        return true;
      }
    }
  }
  // No empty cells found
  return false;
}

void Spawner::initialFill(Board& board) noexcept {
  // Clear the board first
  board.clear();
  
  // Place the first two tiles of value 2 at the beginning of row-major order
  board.set(0, 0, 2);  // First tile
  board.set(0, 1, 2);  // Second tile
}