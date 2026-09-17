#include "QRCodec.h"
#include <stdexcept>
#include <algorithm>
#include <numeric>

QRMatrix QRCodec::encode(const std::string& text) {
  if (text.size() > 40) {
    throw std::invalid_argument("Text size exceeds maximum limit of 40 bytes");
  }

  QRMatrix matrix;

  // Encode the text into bits according to the wire format
  // Length byte
  uint8_t length = static_cast<uint8_t>(text.size());
  // Payload bytes (MSB-first)
  std::vector<bool> bits;
  bits.reserve(8 + 8 * text.size() + 8); // Reserve space for length + payload + checksum

  // Add length
  for (int i = 7; i >= 0; --i) {
    bits.push_back((length >> i) & 1);
  }

  // Add payload
  for (char c : text) {
    uint8_t byte = static_cast<uint8_t>(c);
    for (int i = 7; i >= 0; --i) {
      bits.push_back((byte >> i) & 1);
    }
  }

  // Calculate checksum
  uint8_t checksum = 0;
  for (char c : text) {
    checksum += static_cast<uint8_t>(c);
  }

  // Add checksum
  for (int i = 7; i >= 0; --i) {
    bits.push_back((checksum >> i) & 1);
  }

  // Fill remaining bits with zeros
  while (bits.size() < 366) {
    bits.push_back(false);
  }

  // Fill the matrix with bits
  std::size_t bit_index = 0;
  for (std::size_t row = 0; row < QRMatrix::SIZE; ++row) {
    for (std::size_t col = 0; col < QRMatrix::SIZE; ++col) {
      if (!QRMatrix::isFinderCell(row, col)) {
        matrix.set(row, col, bits[bit_index]);
        ++bit_index;
      }
    }
  }

  return matrix;
}

std::string QRCodec::decode(const QRMatrix& matrix) {
  // Validate finder patterns
  for (std::size_t row = 0; row < QRMatrix::SIZE; ++row) {
    for (std::size_t col = 0; col < QRMatrix::SIZE; ++col) {
      if (QRMatrix::isFinderCell(row, col) && matrix.get(row, col) != QRMatrix::expectedFinderValue(row, col)) {
        throw std::runtime_error("Invalid finder pattern detected");
      }
    }
  }

  // Collect data bits
  std::vector<bool> bits;
  bits.reserve(366);

  for (std::size_t row = 0; row < QRMatrix::SIZE; ++row) {
    for (std::size_t col = 0; col < QRMatrix::SIZE; ++col) {
      if (!QRMatrix::isFinderCell(row, col)) {
        bits.push_back(matrix.get(row, col));
      }
    }
  }

  // Parse length
  uint8_t length = 0;
  for (int i = 0; i < 8; ++i) {
    length |= (bits[i] ? 1 : 0) << (7 - i);
  }

  if (length > 40) {
    throw std::runtime_error("Invalid length in encoded data");
  }

  // Check if we have enough bits for the payload
  if (bits.size() < 8 + 8 * length + 8) {
    throw std::runtime_error("Insufficient data bits for payload");
  }

  // Extract payload
  std::string payload;
  payload.reserve(length);
  for (std::size_t i = 0; i < length; ++i) {
    uint8_t byte = 0;
    for (int j = 0; j < 8; ++j) {
      byte |= (bits[8 + i * 8 + j] ? 1 : 0) << (7 - j);
    }
    payload.push_back(static_cast<char>(byte));
  }

  // Verify checksum
  uint8_t checksum = 0;
  for (char c : payload) {
    checksum += static_cast<uint8_t>(c);
  }

  // Extract checksum from bits
  uint8_t received_checksum = 0;
  for (int i = 0; i < 8; ++i) {
    received_checksum |= (bits[8 + 8 * length + i] ? 1 : 0) << (7 - i);
  }

  if (checksum != received_checksum) {
    throw std::runtime_error("Checksum verification failed");
  }

  // Check for padding
  for (std::size_t i = 8 + 8 * length + 8; i < bits.size(); ++i) {
    if (bits[i]) {
      throw std::runtime_error("Non-zero padding detected");
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