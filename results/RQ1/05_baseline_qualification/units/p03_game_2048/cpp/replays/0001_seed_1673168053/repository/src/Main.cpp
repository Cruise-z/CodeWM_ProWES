#include "Game.h"
#include <iostream>

int main() {
  Game g;
  g.reset();
  
  // Perform a simple left move to demonstrate functionality
  g.move(Move::Direction::Left);
  
  // Print board state
  const Board& board = g.board();
  for (std::size_t r = 0; r < Board::side(); ++r) {
    for (std::size_t c = 0; c < Board::side(); ++c) {
      std::cout << board.at(r, c) << " ";
    }
    std::cout << "\n";
  }
  
  // Print score and state
  std::cout << "Score: " << g.score() << "\n";
  switch (g.state()) {
    case GameState::Ongoing:
      std::cout << "State: Ongoing\n";
      break;
    case GameState::Won:
      std::cout << "State: Won\n";
      break;
    case GameState::Lost:
      std::cout << "State: Lost\n";
      break;
  }
  
  return 0;
}