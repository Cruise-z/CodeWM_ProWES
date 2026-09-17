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
    const std::size_t row_start = origin[0];
    const std::size_t col_start = origin[1];

    // Draw the 5x5 finder pattern
    for (std::size_t i = 0; i < FINDER_SIZE; ++i) {
      for (std::size_t j = 0; j < FINDER_SIZE; ++j) {
        const std::size_t row = row_start + i;
        const std::size_t col = col_start + j;

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
  // Check if the position falls within any of the three 5x5 finder patterns
  const std::size_t finder_origins[3][2] = {{0, 0}, {0, 16}, {16, 0}};

  for (const auto& origin : finder_origins) {
    const std::size_t row_start = origin[0];
    const std::size_t col_start = origin[1];

    // Check if the cell is within the bounds of this finder pattern
    if (row >= row_start && row < row_start + FINDER_SIZE &&
        col >= col_start && col < col_start + FINDER_SIZE) {
      // Inside the finder pattern, check if it's a finder cell
      // Finder pattern structure:
      // 5x5 grid where border is true, inner ring is false, center is true
      if ((row == row_start || row == row_start + FINDER_SIZE - 1 ||
           col == col_start || col == col_start + FINDER_SIZE - 1) ||
          (row == row_start + 1 || row == row_start + FINDER_SIZE - 2 ||
           col == col_start + 1 || col == col_start + FINDER_SIZE - 2)) {
        return true;
      }
    }
  }

  return false;
}

bool QRMatrix::expectedFinderValue(std::size_t row, std::size_t col) {
  // Check if this is a finder cell
  if (!isFinderCell(row, col)) {
    return false;
  }

  // Define the three finder origins
  const std::size_t finder_origins[3][2] = {{0, 0}, {0, 16}, {16, 0}};

  // Find which finder this cell belongs to
  for (const auto& origin : finder_origins) {
    const std::size_t row_start = origin[0];
    const std::size_t col_start = origin[1];

    // Check if the cell is within the bounds of this finder pattern
    if (row >= row_start && row < row_start + FINDER_SIZE &&
        col >= col_start && col < col_start + FINDER_SIZE) {
      // Calculate relative coordinates within the finder
      const std::size_t rel_row = row - row_start;
      const std::size_t rel_col = col - col_start;

      // Finder pattern structure:
      // 5x5 grid where border is true, inner ring is false, center is true
      if (rel_row == 0 || rel_row == FINDER_SIZE - 1 ||
          rel_col == 0 || rel_col == FINDER_SIZE - 1) {
        return true;
      } else if (rel_row == 1 || rel_row == FINDER_SIZE - 2 ||
                 rel_col == 1 || rel_col == FINDER_SIZE - 2) {
        return false;
      } else if (rel_row == 2 && rel_col == 2) {
        return true;
      }
    }
  }

  // This shouldn't happen if isFinderCell was correct, but return false as fallback
  return false;
}