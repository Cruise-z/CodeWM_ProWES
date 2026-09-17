#include "QRCodec.h"
#include <cstdint>
#include <stdexcept>
#include <algorithm>
#include <numeric>

QRMatrix QRCodec::encode(const std::string& text) {
  if (text.size() > 40) {
    throw std::invalid_argument("Text size exceeds maximum allowed (40 bytes)");
  }

  QRMatrix matrix;

  // Write the length as the first 8 bits
  uint8_t length = static_cast<uint8_t>(text.size());
  for (int i = 7; i >= 0; --i) {
    bool bit = (length >> i) & 1;
    // Determine data position in row-major order, skipping finder cells
    int data_pos = 0;
    for (int row = 0; row < QRMatrix::SIZE; ++row) {
      for (int col = 0; col < QRMatrix::SIZE; ++col) {
        if (!QRMatrix::isFinderCell(row, col)) {
          if (data_pos == (7 - i)) {
            matrix.set(row, col, bit);
            break;
          }
          data_pos++;
        }
      }
    }
  }

  // Write the payload bytes MSB-first
  for (size_t i = 0; i < text.size(); ++i) {
    uint8_t byte = static_cast<uint8_t>(text[i]);
    for (int j = 7; j >= 0; --j) {
      bool bit = (byte >> j) & 1;
      // Determine data position in row-major order, skipping finder cells
      int data_pos = 0;
      for (int row = 0; row < QRMatrix::SIZE; ++row) {
        for (int col = 0; col < QRMatrix::SIZE; ++col) {
          if (!QRMatrix::isFinderCell(row, col)) {
            if (data_pos == 8 + (i * 8) + (7 - j)) {
              matrix.set(row, col, bit);
              break;
            }
            data_pos++;
          }
        }
      }
    }
  }

  // Calculate and write the checksum
  uint8_t checksum = std::accumulate(text.begin(), text.end(), 0u) % 256;
  for (int i = 7; i >= 0; --i) {
    bool bit = (checksum >> i) & 1;
    // Determine data position in row-major order, skipping finder cells
    int data_pos = 0;
    for (int row = 0; row < QRMatrix::SIZE; ++row) {
      for (int col = 0; col < QRMatrix::SIZE; ++col) {
        if (!QRMatrix::isFinderCell(row, col)) {
          if (data_pos == 8 + (text.size() * 8) + (7 - i)) {
            matrix.set(row, col, bit);
            break;
          }
          data_pos++;
        }
      }
    }
  }

  // Pad with zeros to fill the rest of the data area
  int data_pos = 8 + (text.size() * 8) + 8;  // Skip length, payload, and checksum
  for (int row = 0; row < QRMatrix::SIZE; ++row) {
    for (int col = 0; col < QRMatrix::SIZE; ++col) {
      if (!QRMatrix::isFinderCell(row, col)) {
        if (data_pos < 366) {  // Total number of data positions
          matrix.set(row, col, false);
          data_pos++;
        } else {
          break;
        }
      }
    }
  }

  return matrix;
}

std::string QRCodec::decode(const QRMatrix& matrix) {
  // Validate finder pattern
  for (int row = 0; row < QRMatrix::SIZE; ++row) {
    for (int col = 0; col < QRMatrix::SIZE; ++col) {
      if (QRMatrix::isFinderCell(row, col)) {
        if (matrix.get(row, col) != QRMatrix::expectedFinderValue(row, col)) {
          throw std::runtime_error("Finder pattern mismatch");
        }
      }
    }
  }

  // Read the length
  uint8_t length = 0;
  int data_pos = 0;
  for (int i = 0; i < 8; ++i) {
    bool bit = false;
    for (int row = 0; row < QRMatrix::SIZE; ++row) {
      for (int col = 0; col < QRMatrix::SIZE; ++col) {
        if (!QRMatrix::isFinderCell(row, col)) {
          if (data_pos == i) {
            bit = matrix.get(row, col);
            break;
          }
          data_pos++;
        }
      }
    }
    length |= (bit ? 1 : 0) << (7 - i);
  }

  if (length > 40) {
    throw std::runtime_error("Invalid length in decoded data");
  }

  // Read the payload
  std::string payload(length, '\0');
  for (size_t i = 0; i < length; ++i) {
    uint8_t byte = 0;
    for (int j = 0; j < 8; ++j) {
      bool bit = false;
      for (int row = 0; row < QRMatrix::SIZE; ++row) {
        for (int col = 0; col < QRMatrix::SIZE; ++col) {
          if (!QRMatrix::isFinderCell(row, col)) {
            if (data_pos == 8 + (i * 8) + j) {
              bit = matrix.get(row, col);
              break;
            }
            data_pos++;
          }
        }
      }
      byte |= (bit ? 1 : 0) << (7 - j);
    }
    payload[i] = static_cast<char>(byte);
  }

  // Read the checksum
  uint8_t checksum = 0;
  for (int i = 0; i < 8; ++i) {
    bool bit = false;
    for (int row = 0; row < QRMatrix::SIZE; ++row) {
      for (int col = 0; col < QRMatrix::SIZE; ++col) {
        if (!QRMatrix::isFinderCell(row, col)) {
          if (data_pos == 8 + (length * 8) + i) {
            bit = matrix.get(row, col);
            break;
          }
          data_pos++;
        }
      }
    }
    checksum |= (bit ? 1 : 0) << (7 - i);
  }

  // Verify checksum
  uint8_t calculated_checksum = std::accumulate(payload.begin(), payload.end(), 0u) % 256;
  if (checksum != calculated_checksum) {
    throw std::runtime_error("Checksum validation failed");
  }

  // Check padding
  for (int row = 0; row < QRMatrix::SIZE; ++row) {
    for (int col = 0; col < QRMatrix::SIZE; ++col) {
      if (!QRMatrix::isFinderCell(row, col)) {
        if (data_pos < 366) {
          if (matrix.get(row, col) != false) {
            throw std::runtime_error("Non-zero padding detected");
          }
          data_pos++;
        } else {
          break;
        }
      }
    }
  }

  return payload;
}

bool QRCodec::detect(const QRMatrix& matrix) noexcept {
  try {
    decode(matrix);
    return true;
  } catch (...) {
    return false;
  }
}