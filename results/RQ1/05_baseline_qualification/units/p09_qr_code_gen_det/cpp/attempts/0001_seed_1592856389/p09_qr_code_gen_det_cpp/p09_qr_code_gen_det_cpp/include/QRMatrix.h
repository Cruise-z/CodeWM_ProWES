#pragma once

#include <array>
#include <cstddef>
#include <stdexcept>

/**
 * A fixed 21x21 QR code matrix with three 5x5 finder patterns.
 *
 * This class represents a QR code matrix with a fixed size of 21x21 modules.
 * It includes three 5x5 finder patterns positioned at (0,0), (0,16), and (16,0).
 * All other cells are data cells. The finder patterns follow the standard
 * QR code specification where:
 * - The border of each finder pattern is true
 * - The inner ring is false
 * - The center cell (2,2) within each finder is true
 */
class QRMatrix {
 public:
  /// Size of the QR matrix in modules
  static constexpr std::size_t SIZE = 21;
  
  /// Size of each finder pattern in modules
  static constexpr std::size_t FINDER_SIZE = 5;

  /**
   * Constructs a new QRMatrix with all modules initialized to false,
   * then places three finder patterns.
   */
  QRMatrix();

  /**
   * Gets the value of a module at the specified coordinates.
   *
   * @param row Row index (0-20)
   * @param col Column index (0-20)
   * @return True if the module is set, false otherwise
   * @throws std::out_of_range if row or col are outside the valid range [0, 20]
   */
  bool get(std::size_t row, std::size_t col) const;

  /**
   * Sets the value of a module at the specified coordinates.
   *
   * @param row Row index (0-20)
   * @param col Column index (0-20)
   * @param value The boolean value to set
   * @throws std::out_of_range if row or col are outside the valid range [0, 20]
   */
  void set(std::size_t row, std::size_t col, bool value);

  /**
   * Checks if a given coordinate corresponds to a finder pattern cell.
   *
   * @param row Row index (0-20)
   * @param col Column index (0-20)
   * @return True if the cell belongs to a finder pattern, false otherwise
   */
  static bool isFinderCell(std::size_t row, std::size_t col);

  /**
   * Gets the expected value of a finder cell.
   *
   * @param row Row index (0-20)
   * @param col Column index (0-20)
   * @return Expected value (true for border, false for inner area, true for center)
   */
  static bool expectedFinderValue(std::size_t row, std::size_t col);

 private:
  /// Storage for the 21x21 modules
  std::array<std::array<bool, SIZE>, SIZE> modules_{};
  
  /**
   * Initializes the three finder patterns at their standard positions.
   * 
   * Finders are placed at:
   * - Top-left: (0, 0)
   * - Top-right: (0, 16)
   * - Bottom-left: (16, 0)
   * Each finder follows the standard pattern:
   * - Border: true
   * - Inner ring: false
   * - Center (2,2): true
   */
  void InitializeFinders();
};