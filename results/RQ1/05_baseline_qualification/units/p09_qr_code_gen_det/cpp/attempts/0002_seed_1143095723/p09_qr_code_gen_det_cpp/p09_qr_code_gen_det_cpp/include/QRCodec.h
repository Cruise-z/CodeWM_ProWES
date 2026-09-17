#pragma once

#include <string>
#include "QRMatrix.h"

class QRCodec {
 public:
  /// Encodes a string into a QRMatrix.
  /// @param text The input string to encode (max 40 bytes).
  /// @return A QRMatrix representing the encoded data.
  /// @throws std::invalid_argument if text.size() > 40.
  static QRMatrix encode(const std::string& text);

  /// Decodes a QRMatrix into a string.
  /// @param matrix The QRMatrix to decode.
  /// @return The decoded string.
  /// @throws std::runtime_error if the matrix is invalid (finder pattern mismatch,
  ///         incorrect length, invalid checksum, or non-zero padding).
  static std::string decode(const QRMatrix& matrix);

  /// Detects whether a QRMatrix contains valid encoded data.
  /// @param matrix The QRMatrix to detect.
  /// @return true if the matrix can be successfully decoded, false otherwise.
  /// @note This function is noexcept and will never throw exceptions.
  static bool detect(const QRMatrix& matrix) noexcept;
};