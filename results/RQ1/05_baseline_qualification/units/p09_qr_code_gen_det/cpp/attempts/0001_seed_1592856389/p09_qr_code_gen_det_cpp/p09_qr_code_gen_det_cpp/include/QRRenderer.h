#pragma once

#include <string>
#include "QRMatrix.h"

/**
 * QR Renderer for converting QRMatrix to ASCII representation.
 *
 * This class provides a static method to render a QRMatrix as an ASCII string
 * using customizable markers for on/off modules. The output is guaranteed to
 * contain exactly 21 lines separated by exactly 20 newline characters with
 * no trailing newline.
 */
class QRRenderer {
 public:
  /**
   * Renders a QRMatrix as an ASCII string.
   *
   * @param matrix The QRMatrix to render
   * @param on The string to use for modules that are true (default: "##")
   * @param off The string to use for modules that are false (default: "  ")
   * @return A string containing exactly 21 lines separated by exactly 20 newlines
   * @throws std::invalid_argument if on or off strings are empty
   */
  static std::string render(const QRMatrix& matrix,
                            const std::string& on = "##",
                            const std::string& off = "  ");
};