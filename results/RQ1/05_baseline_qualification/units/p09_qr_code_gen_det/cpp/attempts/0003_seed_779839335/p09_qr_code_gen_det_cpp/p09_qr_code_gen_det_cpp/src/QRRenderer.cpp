#include "QRRenderer.h"
#include <string>
#include <stdexcept>

std::string QRRenderer::render(const QRMatrix& matrix,
                               const std::string& on,
                               const std::string& off) {
  // Validate markers
  if (on.empty() || off.empty()) {
    throw std::invalid_argument("Markers cannot be empty");
  }

  std::string result;
  result.reserve(21 * (2 * 21 + 20)); // Pre-allocate for efficiency

  for (std::size_t row = 0; row < QRMatrix::SIZE; ++row) {
    for (std::size_t col = 0; col < QRMatrix::SIZE; ++col) {
      if (matrix.get(row, col)) {
        result += on;
      } else {
        result += off;
      }
    }
    // Add newline after each row except the last one
    if (row < QRMatrix::SIZE - 1) {
      result += '\n';
    }
  }

  // Ensure exactly 21 lines and 20 newlines
  // Count newlines in result
  std::size_t newline_count = 0;
  for (char c : result) {
    if (c == '\n') {
      newline_count++;
    }
  }

  // Verify the count is exactly 20 (21 lines, 20 newlines between them)
  if (newline_count != 20) {
    throw std::runtime_error("Rendered matrix does not have exactly 20 newlines");
  }

  return result;
}