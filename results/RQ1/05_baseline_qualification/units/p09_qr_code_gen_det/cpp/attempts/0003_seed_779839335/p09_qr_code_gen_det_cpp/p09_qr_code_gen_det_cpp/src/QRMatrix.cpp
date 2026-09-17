#include "QRMatrix.h"

QRMatrix::QRMatrix() {
  // Initialize all modules to false
  for (std::size_t i = 0; i < SIZE; ++i) {
    for (std::size_t j = 0; j < SIZE; ++j) {
      modules_[i][j] = false;
    }
  }

  // Define the three finder patterns at (0,0), (0,16), and (16,0)
  const std::size_t finder_origins[3][2] = {{0, 0}, {0, 16}, {16, 0}};

  for (const auto& origin : finder_origins) {
    const std::size_t row_origin = origin[0];
    const std::size_t col_origin = origin[1];

    // Draw the 5x5 finder pattern
    for (std::size_t i = 0; i < FINDER_SIZE; ++i) {
      for (std::size_t j = 0; j < FINDER_SIZE; ++j) {
        const std::size_t row = row_origin + i;
        const std::size_t col = col_origin + j;

        // Border is true
        if (i == 0 || i == FINDER_SIZE - 1 || j == 0 || j == FINDER_SIZE - 1) {
          modules_[row][col] = true;
        }
        // Inner ring is false
        else if (i == 1 || i == FINDER_SIZE - 2 || j == 1 || j == FINDER_SIZE - 2) {
          modules_[row][col] = false;
        }
        // Center is true
        else if (i == 2 && j == 2) {
          modules_[row][col] = true;
        }
      }
    }
  }
}

bool QRMatrix::get(std::size_t row, std::size_t col) const {
  if (row >= SIZE || col >= SIZE) {
    throw std::out_of_range("Accessing QRMatrix out of bounds");
  }
  return modules_[row][col];
}

void QRMatrix::set(std::size_t row, std::size_t col, bool value) {
  if (row >= SIZE || col >= SIZE) {
    throw std::out_of_range("Setting QRMatrix out of bounds");
  }
  modules_[row][col] = value;
}

bool QRMatrix::isFinderCell(std::size_t row, std::size_t col) {
  // Finder pattern is 5x5 at (0,0), (0,16), (16,0)
  const std::size_t finder_origins[3][2] = {{0, 0}, {0, 16}, {16, 0}};
  
  for (const auto& origin : finder_origins) {
    const std::size_t row_origin = origin[0];
    const std::size_t col_origin = origin[1];
    
    if (row >= row_origin && row < row_origin + FINDER_SIZE &&
        col >= col_origin && col < col_origin + FINDER_SIZE) {
      return true;
    }
  }
  return false;
}

bool QRMatrix::expectedFinderValue(std::size_t row, std::size_t col) {
  // Finder pattern is 5x5 at (0,0), (0,16), (16,0)
  const std::size_t finder_origins[3][2] = {{0, 0}, {0, 16}, {16, 0}};
  
  for (const auto& origin : finder_origins) {
    const std::size_t row_origin = origin[0];
    const std::size_t col_origin = origin[1];
    
    if (row >= row_origin && row < row_origin + FINDER_SIZE &&
        col >= col_origin && col < col_origin + FINDER_SIZE) {
      
      // Border is true
      if (row == row_origin || row == row_origin + FINDER_SIZE - 1 ||
          col == col_origin || col == col_origin + FINDER_SIZE - 1) {
        return true;
      }
      // Inner ring is false
      else if (row == row_origin + 1 || row == row_origin + FINDER_SIZE - 2 ||
               col == col_origin + 1 || col == col_origin + FINDER_SIZE - 2) {
        return false;
      }
      // Center is true
      else if (row == row_origin + 2 && col == col_origin + 2) {
        return true;
      }
    }
  }
  return false;
}