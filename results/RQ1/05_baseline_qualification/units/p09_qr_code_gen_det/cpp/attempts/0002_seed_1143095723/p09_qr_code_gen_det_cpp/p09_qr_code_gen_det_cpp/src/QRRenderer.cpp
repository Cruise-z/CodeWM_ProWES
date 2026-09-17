#include "QRRenderer.h"
#include <stdexcept>
#include <string>

std::string QRRenderer::render(const QRMatrix& matrix,
                               const std::string& on,
                               const std::string& off) {
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

  // Verify we have exactly 21 lines and 20 newlines
  // Count newlines to ensure correctness
  int newline_count = 0;
  for (char c : result) {
    if (c == '\n') {
      newline_count++;
    }
  }
  
  // Should be exactly 20 newlines (20 separating 21 lines)
  if (newline_count != 20) {
    // This should not happen given our logic, but we include it for robustness
    throw std::runtime_error("Rendered output does not contain exactly 20 newlines");
  }

  return result;
}