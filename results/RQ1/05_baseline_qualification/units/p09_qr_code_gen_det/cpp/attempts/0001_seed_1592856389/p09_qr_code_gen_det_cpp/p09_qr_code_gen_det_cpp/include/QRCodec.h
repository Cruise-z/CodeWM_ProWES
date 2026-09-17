#pragma once

#include <string>
#include "QRMatrix.h"

/**
 * QR Codec for encoding, decoding, and detecting QR codes.
 *
 * This class provides static methods for encoding text into a QRMatrix,
 * decoding a QRMatrix back into text, and detecting whether a QRMatrix
 * contains valid QR code data according to the specified format.
 */
class QRCodec {
 public:
  /**
   * Encodes a string into a QRMatrix.
   *
   * @param text The text to encode (max 40 bytes)
   * @return A QRMatrix representing the encoded data
   * @throws std::invalid_argument if text.size() > 40
   */
  static QRMatrix encode(const std::string& text);

  /**
   * Decodes a QRMatrix into a string.
   *
   * @param matrix The QRMatrix to decode
   * @return The decoded string
   * @throws std::runtime_error if the matrix is invalid (finder mismatch,
   *                            checksum error, length error, or padding error)
   */
  static std::string decode(const QRMatrix& matrix);

  /**
   * Detects whether a QRMatrix contains valid QR code data.
   *
   * @param matrix The QRMatrix to check
   * @return true if the matrix is valid and can be decoded, false otherwise
   */
  static bool detect(const QRMatrix& matrix) noexcept;
};