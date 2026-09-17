#pragma once

#include <string>
#include "QRMatrix.h"

class QRRenderer {
 public:
  static std::string render(const QRMatrix& matrix,
                            const std::string& on = "##",
                            const std::string& off = "  ");
};