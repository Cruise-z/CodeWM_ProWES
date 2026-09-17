#include "QRCodec.h"
#include <algorithm>
#include <numeric>
#include <cstdint>

QRMatrix QRCodec::encode(const std::string& text) {
  if (text.size() > 40) {
    throw std::invalid_argument("Text length exceeds maximum of 40 bytes");
  }

  QRMatrix matrix;
  
  // Calculate the checksum
  uint8_t checksum = 0;
  if (!text.empty()) {
    checksum = std::accumulate(text.begin(), text.end(), 0, [](uint8_t acc, char c) {
      return acc + static_cast<uint8_t>(c);
    }) & 0xFF;
  }

  // Prepare the bit stream
  std::vector<bool> bits;
  
  // Add length byte
  bits.push_back((text.size() & 0x80) != 0);
  bits.push_back((text.size() & 0x40) != 0);
  bits.push_back((text.size() & 0x20) != 0);
  bits.push_back((text.size() & 0x10) != 0);
  bits.push_back((text.size() & 0x08) != 0);
  bits.push_back((text.size() & 0x04) != 0);
  bits.push_back((text.size() & 0x02) != 0);
  bits.push_back((text.size() & 0x01) != 0);
  
  // Add payload bytes MSB-first
  for (char c : text) {
    uint8_t byte = static_cast<uint8_t>(c);
    bits.push_back((byte & 0x80) != 0);
    bits.push_back((byte & 0x40) != 0);
    bits.push_back((byte & 0x20) != 0);
    bits.push_back((byte & 0x10) != 0);
    bits.push_back((byte & 0x08) != 0);
    bits.push_back((byte & 0x04) != 0);
    bits.push_back((byte & 0x02) != 0);
    bits.push_back((byte & 0x01) != 0);
  }
  
  // Add checksum byte
  bits.push_back((checksum & 0x80) != 0);
  bits.push_back((checksum & 0x40) != 0);
  bits.push_back((checksum & 0x20) != 0);
  bits.push_back((checksum & 0x10) != 0);
  bits.push_back((checksum & 0x08) != 0);
  bits.push_back((checksum & 0x04) != 0);
  bits.push_back((checksum & 0x02) != 0);
  bits.push_back((checksum & 0x01) != 0);
  
  // Pad with zeros to fill the rest of the 366 bits
  while (bits.size() < 366) {
    bits.push_back(false);
  }
  
  // Fill the matrix with data bits
  std::size_t bit_index = 0;
  for (std::size_t row = 0; row < QRMatrix::SIZE; ++row) {
    for (std::size_t col = 0; col < QRMatrix::SIZE; ++col) {
      if (!QRMatrix::isFinderCell(row, col)) {
        matrix.set(row, col, bits[bit_index]);
        bit_index++;
      }
    }
  }
  
  return matrix;
}

std::string QRCodec::decode(const QRMatrix& matrix) {
  // Validate finder patterns
  for (std::size_t row = 0; row < QRMatrix::SIZE; ++row) {
    for (std::size_t col = 0; col < QRMatrix::SIZE; ++col) {
      if (QRMatrix::isFinderCell(row, col) && 
          matrix.get(row, col) != QRMatrix::expectedFinderValue(row, col)) {
        throw std::runtime_error("Finder pattern mismatch");
      }
    }
  }
  
  // Read the data bits
  std::vector<bool> bits;
  for (std::size_t row = 0; row < QRMatrix::SIZE; ++row) {
    for (std::size_t col = 0; col < QRMatrix::SIZE; ++col) {
      if (!QRMatrix::isFinderCell(row, col)) {
        bits.push_back(matrix.get(row, col));
      }
    }
  }
  
  // Parse the length from the first 8 bits
  std::size_t length = 0;
  for (int i = 0; i < 8; ++i) {
    length <<= 1;
    length |= bits[i] ? 1 : 0;
  }
  
  // Validate length
  if (length > 40 || bits.size() < 8 + length * 8 + 8) {
    throw std::runtime_error("Invalid length or insufficient data");
  }
  
  // Read payload bytes
  std::string payload;
  for (std::size_t i = 0; i < length; ++i) {
    uint8_t byte = 0;
    for (int j = 0; j < 8; ++j) {
      byte <<= 1;
      byte |= bits[8 + i * 8 + j] ? 1 : 0;
    }
    payload += static_cast<char>(byte);
  }
  
  // Verify checksum
  uint8_t checksum = 0;
  if (!payload.empty()) {
    checksum = std::accumulate(payload.begin(), payload.end(), 0, [](uint8_t acc, char c) {
      return acc + static_cast<uint8_t>(c);
    }) & 0xFF;
  }
  
  // Read the checksum byte
  uint8_t received_checksum = 0;
  for (int i = 0; i < 8; ++i) {
    received_checksum <<= 1;
    received_checksum |= bits[8 + length * 8 + i] ? 1 : 0;
  }
  
  if (checksum != received_checksum) {
    throw std::runtime_error("Checksum mismatch");
  }
  
  // Check that remaining bits are all zero
  for (std::size_t i = 8 + length * 8 + 8; i < bits.size(); ++i) {
    if (bits[i]) {
      throw std::runtime_error("Non-zero padding bits");
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