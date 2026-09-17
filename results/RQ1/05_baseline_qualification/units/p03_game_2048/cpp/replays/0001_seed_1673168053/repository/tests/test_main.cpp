#include <cassert>
#include <cstdint>
#include "Game.h"
#include "Move.h"

int main() {
  // Test 1: Game construction/reset produces deterministic starting board
  {
    Game g;
    g.reset();
    
    // Check that the board has exactly two 2s in the first two positions
    const Board& board = g.board();
    assert(board.at(0, 0) == 2);  // First tile
    assert(board.at(0, 1) == 2);  // Second tile
    assert(board.at(0, 2) == 0);  // Empty
    assert(board.at(0, 3) == 0);  // Empty
    assert(board.at(1, 0) == 0);  // Empty
    assert(board.at(1, 1) == 0);  // Empty
    assert(board.at(1, 2) == 0);  // Empty
    assert(board.at(1, 3) == 0);  // Empty
    assert(board.at(2, 0) == 0);  // Empty
    assert(board.at(2, 1) == 0);  // Empty
    assert(board.at(2, 2) == 0);  // Empty
    assert(board.at(2, 3) == 0);  // Empty
    assert(board.at(3, 0) == 0);  // Empty
    assert(board.at(3, 1) == 0);  // Empty
    assert(board.at(3, 2) == 0);  // Empty
    assert(board.at(3, 3) == 0);  // Empty
    
    // Check that the score is 0
    assert(g.score() == 0);
    
    // Check that the state is Ongoing
    assert(g.state() == GameState::Ongoing);
  }
  
  // Test 2: Representative line merge rule via Move::processLine
  {
    // Test slide-merge-slide with single merge per tile
    std::array<std::uint16_t, 4> line = {2, 2, 4, 0};
    auto result = Move::processLine(line);
    
    // Should merge the first two 2s into 4, shift everything left
    assert(result.line[0] == 4);   // First merged 2
    assert(result.line[1] == 4);   // The 4 from input
    assert(result.line[2] == 0);   // Shifted
    assert(result.line[3] == 0);   // Shifted
    assert(result.moved == true);  // Something changed
    assert(result.scoreGained == 4);  // Score is post-merge value (4)
    
    // Test another case: no merge, just sliding
    std::array<std::uint16_t, 4> line2 = {2, 4, 8, 16};
    auto result2 = Move::processLine(line2);
    
    assert(result2.line[0] == 2);   // Unchanged
    assert(result2.line[1] == 4);   // Unchanged
    assert(result2.line[2] == 8);   // Unchanged
    assert(result2.line[3] == 16);  // Unchanged
    assert(result2.moved == false); // No change
    assert(result2.scoreGained == 0); // No merge
    
    // Test merge at the end
    std::array<std::uint16_t, 4> line3 = {2, 4, 4, 2};
    auto result3 = Move::processLine(line3);
    
    assert(result3.line[0] == 2);   // First 2 unchanged
    assert(result3.line[1] == 8);   // Merged 4+4=8
    assert(result3.line[2] == 2);   // Last 2 unchanged
    assert(result3.line[3] == 0);   // Shifted
    assert(result3.moved == true);  // Changed
    assert(result3.scoreGained == 8); // Score is post-merge value (8)
  }
  
  // Test 3: A simple move updates board and score deterministically
  {
    Game g;
    g.reset();
    
    // Perform a left move
    bool moved = g.move(Move::Direction::Left);
    
    // Should have moved since we started with two 2s at (0,0) and (0,1)
    assert(moved == true);
    
    // After moving left, the board should have 4 at (0,0) and 4 at (0,1)
    const Board& board = g.board();
    assert(board.at(0, 0) == 4);  // First 2 merged with second 2
    assert(board.at(0, 1) == 4);  // Second 2 merged with first 2
    assert(board.at(0, 2) == 0);  // Shifted empty
    assert(board.at(0, 3) == 0);  // Shifted empty
    
    // Score should be 4 (post-merge value of 2+2)
    assert(g.score() == 4);
    
    // State should still be Ongoing
    assert(g.state() == GameState::Ongoing);
  }
  
  return 0;
}