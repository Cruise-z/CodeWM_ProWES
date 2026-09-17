#include "Move.h"
#include "Board.h"
#include <algorithm>
#include <numeric>

namespace Move {

namespace {
  /**
   * @brief Slides non-zero elements of a line to the left, filling empty spaces with zeros.
   * @param line Input line to slide.
   * @return Line with elements slid to the left.
   */
  std::array<std::uint16_t, 4> slide(const std::array<std::uint16_t, 4>& line) noexcept {
    std::array<std::uint16_t, 4> result{};
    std::size_t dst = 0;
    
    // Copy non-zero elements to the left
    for (std::size_t src = 0; src < 4; ++src) {
      if (line[src] != 0) {
        result[dst++] = line[src];
      }
    }
    
    return result;
  }

  /**
   * @brief Merges adjacent equal elements in a line from left to right, 
   *        doubling the left value and zeroing the right.
   * @param line Input line to merge.
   * @return Line after merging and scoring.
   */
  LineMoveResult merge(const std::array<std::uint16_t, 4>& line) noexcept {
    std::array<std::uint16_t, 4> result = line;
    std::uint32_t score_gained = 0;
    bool merged = false;
    
    // Process from left to right, merging each pair once
    for (std::size_t i = 0; i < 3; ++i) {
      if (result[i] != 0 && result[i] == result[i+1]) {
        result[i] *= 2;
        score_gained += result[i];  // Score is post-merge value
        result[i+1] = 0;
        merged = true;
      }
    }
    
    return {result, merged, score_gained};
  }

  /**
   * @brief Applies slide-merge-slide operation to a line.
   * @param line Input line.
   * @return Result of the full operation including final line, moved flag, and score.
   */
  LineMoveResult slideMergeSlide(const std::array<std::uint16_t, 4>& line) noexcept {
    // Step 1: Slide left
    auto slid = slide(line);
    
    // Step 2: Merge
    auto merged = merge(slid);
    
    // Step 3: Slide again
    auto final_line = slide(merged.line);
    
    // Determine if anything changed
    bool moved = (line != final_line);
    
    return {final_line, moved, merged.scoreGained};
  }
}  // namespace

LineMoveResult processLine(const std::array<std::uint16_t, 4>& line) noexcept {
  return slideMergeSlide(line);
}

BoardMoveResult applyMove(Board& board, Direction dir) noexcept {
  BoardMoveResult result{false, 0};
  
  switch (dir) {
    case Direction::Left: {
      // Process each row
      for (std::size_t r = 0; r < 4; ++r) {
        std::array<std::uint16_t, 4> row;
        board.getRow(r, row);
        auto row_result = slideMergeSlide(row);
        
        if (row_result.moved) {
          board.setRow(r, row_result.line);
          result.moved = true;
          result.scoreGained += row_result.scoreGained;
        }
      }
      break;
    }
    
    case Direction::Right: {
      // Process each row in reverse order (rightmost first)
      for (std::size_t r = 0; r < 4; ++r) {
        std::array<std::uint16_t, 4> row;
        board.getRow(r, row);
        // Reverse for processing
        std::reverse(row.begin(), row.end());
        auto row_result = slideMergeSlide(row);
        
        if (row_result.moved) {
          // Reverse back before setting
          std::reverse(row_result.line.begin(), row_result.line.end());
          board.setRow(r, row_result.line);
          result.moved = true;
          result.scoreGained += row_result.scoreGained;
        }
      }
      break;
    }
    
    case Direction::Up: {
      // Process each column
      for (std::size_t c = 0; c < 4; ++c) {
        std::array<std::uint16_t, 4> col;
        board.getCol(c, col);
        auto col_result = slideMergeSlide(col);
        
        if (col_result.moved) {
          board.setCol(c, col_result.line);
          result.moved = true;
          result.scoreGained += col_result.scoreGained;
        }
      }
      break;
    }
    
    case Direction::Down: {
      // Process each column in reverse order
      for (std::size_t c = 0; c < 4; ++c) {
        std::array<std::uint16_t, 4> col;
        board.getCol(c, col);
        // Reverse for processing
        std::reverse(col.begin(), col.end());
        auto col_result = slideMergeSlide(col);
        
        if (col_result.moved) {
          // Reverse back before setting
          std::reverse(col_result.line.begin(), col_result.line.end());
          board.setCol(c, col_result.line);
          result.moved = true;
          result.scoreGained += col_result.scoreGained;
        }
      }
      break;
    }
  }
  
  return result;
}

bool hasLegalMove(const Board& board) noexcept {
  // Check for any empty cells
  if (board.hasEmpty()) {
    return true;
  }
  
  // Check for adjacent equal tiles in all directions
  // We'll check left/right adjacency and up/down adjacency
  
  // Horizontal adjacent checks (left/right)
  for (std::size_t r = 0; r < 4; ++r) {
    std::array<std::uint16_t, 4> row;
    board.getRow(r, row);
    for (std::size_t c = 0; c < 3; ++c) {
      if (row[c] == row[c+1]) {
        return true;
      }
    }
  }
  
  // Vertical adjacent checks (up/down)
  for (std::size_t c = 0; c < 4; ++c) {
    std::array<std::uint16_t, 4> col;
    board.getCol(c, col);
    for (std::size_t r = 0; r < 3; ++r) {
      if (col[r] == col[r+1]) {
        return true;
      }
    }
  }
  
  return false;
}

}  // namespace Move