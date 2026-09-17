#include "QRMatrix.h"

QRMatrix::QRMatrix() {
  // Initialize all modules to false
  for (auto& row : modules_) {
    row.fill(false);
  }
  
  // Initialize the three finder patterns
  InitializeFinders();
}

bool QRMatrix::get(std::size_t row, std::size_t col) const {
  if (row >= SIZE || col >= SIZE) {
    throw std::out_of_range("QRMatrix::get: index out of range");
  }
  return modules_[row][col];
}

void QRMatrix::set(std::size_t row, std::size_t col, bool value) {
  if (row >= SIZE || col >= SIZE) {
    throw std::out_of_range("QRMatrix::set: index out of range");
  }
  modules_[row][col] = value;
}

bool QRMatrix::isFinderCell(std::size_t row, std::size_t col) {
  // Check if the cell is within any of the three finder pattern areas
  return (row >= 0 && row < FINDER_SIZE && col >= 0 && col < FINDER_SIZE) ||
         (row >= 0 && row < FINDER_SIZE && col >= SIZE - FINDER_SIZE && col < SIZE) ||
         (row >= SIZE - FINDER_SIZE && row < SIZE && col >= 0 && col < FINDER_SIZE);
}

bool QRMatrix::expectedFinderValue(std::size_t row, std::size_t col) {
  // If not a finder cell, return false as it's not part of the finder pattern
  if (!isFinderCell(row, col)) {
    return false;
  }

  // Calculate relative position within the finder pattern
  std::size_t rel_row = row % FINDER_SIZE;
  std::size_t rel_col = col % FINDER_SIZE;

  // Check if it's on the border (true)
  if (rel_row == 0 || rel_row == FINDER_SIZE - 1 || rel_col == 0 || rel_col == FINDER_SIZE - 1) {
    return true;
  }

  // Check if it's in the inner ring (false)
  if (rel_row == 1 || rel_row == FINDER_SIZE - 2 || rel_col == 1 || rel_col == FINDER_SIZE - 2) {
    return false;
  }

  // It must be the center cell (2,2) which should be true
  return true;
}

void QRMatrix::InitializeFinders() {
  // Top-left finder pattern at (0, 0)
  for (std::size_t i = 0; i < FINDER_SIZE; ++i) {
    for (std::size_t j = 0; j < FINDER_SIZE; ++j) {
      // Set the border to true
      if (i == 0 || i == FINDER_SIZE - 1 || j == 0 || j == FINDER_SIZE - 1) {
        modules_[i][j] = true;
      } else if (i == 2 && j == 2) {
        // Set the center to true
        modules_[i][j] = true;
      } else {
        // Set the inner ring to false
        modules_[i][j] = false;
      }
    }
  }

  // Top-right finder pattern at (0, 16)
  for (std::size_t i = 0; i < FINDER_SIZE; ++i) {
    for (std::size_t j = 0; j < FINDER_SIZE; ++j) {
      // Set the border to true
      if (i == 0 || i == FINDER_SIZE - 1 || j == 0 || j == FINDER_SIZE - 1) {
        modules_[i][j + (SIZE - FINDER_SIZE)] = true;
      } else if (i == 2 && j == 2) {
        // Set the center to true
        modules_[i][j + (SIZE - FINDER_SIZE)] = true;
      } else {
        // Set the inner ring to false
        modules_[i][j + (SIZE - FINDER_SIZE)] = false;
      }
    }
  }

  // Bottom-left finder pattern at (16, 0)
  for (std::size_t i = 0; i < FINDER_SIZE; ++i) {
    for (std::size_t j = 0; j < FINDER_SIZE; ++j) {
      // Set the border to true
      if (i == 0 || i == FINDER_SIZE - 1 || j == 0 || j == FINDER_SIZE - 1) {
        modules_[i + (SIZE - FINDER_SIZE)][j] = true;
      } else if (i == 2 && j == 2) {
        // Set the center to true
        modules_[i + (SIZE - FINDER_SIZE)][j] = true;
      } else {
        // Set the inner ring to false
        modules_[i + (SIZE - FINDER_SIZE)][j] = false;
      }
    }
  }
}