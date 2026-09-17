#pragma once

#include <string>
#include "QRMatrix.h"

class QRRenderer {
 public:
  /// Renders a QRMatrix as an ASCII string.
  /// @param matrix The QRMatrix to render.
  /// @param on The string to use for "on" modules (default: "##").
  /// @param off The string to use for "off" modules (default: "  ").
  /// @return A string containing exactly 21 lines separated by exactly 20 newline characters, with no trailing newline.
  /// @throws std::invalid_argument if either marker string is empty.
  static std::string render(const QRMatrix& matrix,
                            const std::string& on = "##",
                            const std::string& off = "  ");
};