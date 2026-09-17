#include "QRRenderer.h"
#include <stdexcept>
#include <string>

std::string QRRenderer::render(const QRMatrix& matrix,
                               const std::string& on,
                               const std::string& off) {
  // Validate markers
  if (on.empty() || off.empty()) {
    throw std::invalid_argument("Markers cannot be empty");
  }

  std::string result;
  result.reserve(QRMatrix::SIZE * (on.length() + off.length()) + QRMatrix::SIZE - 1);
  
  // Render each row
  for (std::size_t row = 0; row < QRMatrix::SIZE; ++row) {
    // Render each column in the current row
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
  
  return result;
}