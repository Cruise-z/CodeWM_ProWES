#pragma once

#include <string>
#include "QRMatrix.h"

class QRCodec {
 public:
  static QRMatrix encode(const std::string& text);
  static std::string decode(const QRMatrix& matrix);
  static bool detect(const QRMatrix& matrix) noexcept;
};