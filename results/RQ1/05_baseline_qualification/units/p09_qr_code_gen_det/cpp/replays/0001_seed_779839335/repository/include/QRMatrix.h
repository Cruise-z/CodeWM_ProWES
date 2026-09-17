#pragma once

#include <array>
#include <cstddef>
#include <stdexcept>

class QRMatrix {
 public:
  static constexpr std::size_t SIZE = 21;
  static constexpr std::size_t FINDER_SIZE = 5;

  QRMatrix();

  bool get(std::size_t row, std::size_t col) const;
  void set(std::size_t row, std::size_t col, bool value);

  static bool isFinderCell(std::size_t row, std::size_t col);
  static bool expectedFinderValue(std::size_t row, std::size_t col);

 private:
  std::array<std::array<bool, SIZE>, SIZE> modules_{};
};