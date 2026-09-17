#include "Game.h"
#include "IRandom.h"
#include "Types.h"
#include <iostream>

int main() {
  // Create a deterministic random number generator with a fixed seed
  snake::DefaultRandom rng(42);
  
  // Create a game with a small board
  snake::Game game(10, 10, rng);
  
  // Print initial game state
  std::cout << "Initial state:" << std::endl;
  std::cout << "Score: " << game.getScore() << std::endl;
  std::cout << "Food: ";
  if (game.getFood().has_value()) {
    auto food = game.getFood().value();
    std::cout << "(" << food.x << ", " << food.y << ")" << std::endl;
  } else {
    std::cout << "none" << std::endl;
  }
  
  // Tick the game a few times
  for (int i = 0; i < 5; ++i) {
    game.tick();
    std::cout << "\nAfter tick " << (i+1) << ":" << std::endl;
    std::cout << "Score: " << game.getScore() << std::endl;
    std::cout << "Food: ";
    if (game.getFood().has_value()) {
      auto food = game.getFood().value();
      std::cout << "(" << food.x << ", " << food.y << ")" << std::endl;
    } else {
      std::cout << "none" << std::endl;
    }
    std::cout << "Game Over: " << (game.isGameOver() ? "Yes" : "No") << std::endl;
  }
  
  return 0;
}