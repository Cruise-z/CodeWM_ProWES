#include "Game.h"
#include "IRandom.h"
#include "Types.h"
#include <cassert>
#include <cstdint>

// Test that demonstrates basic wiring and core rule: food consumption
int main() {
  // Use a fixed seed for deterministic tests
  snake::DefaultRandom rng(12345);
  
  // Create a small game board
  snake::Game game(5, 5, rng);
  
  // Verify initial state
  assert(game.getScore() == 0);
  assert(game.isGameOver() == false);
  assert(game.getSnake().body().size() == 3);
  
  // Verify initial snake position is at center going right
  auto snakeBody = game.getSnake().body();
  assert(snakeBody[0].x == 2);  // Head
  assert(snakeBody[0].y == 2);
  assert(snakeBody[1].x == 1);  // Middle segment
  assert(snakeBody[1].y == 2);
  assert(snakeBody[2].x == 0);  // Tail
  assert(snakeBody[2].y == 2);
  
  // Verify initial food exists
  assert(game.getFood().has_value());
  
  // Move the snake up to eat food
  game.setDirection(snake::Direction::Up);
  game.tick();
  
  // After the tick, snake should have grown and score incremented
  assert(game.getScore() == 1);
  assert(game.getSnake().body().size() == 4);
  
  // Food should have been replaced
  assert(game.getFood().has_value());
  
  // Try to reverse direction (should be ignored)
  game.setDirection(snake::Direction::Down);
  game.tick();
  
  // Score and size should remain unchanged
  assert(game.getScore() == 1);
  assert(game.getSnake().body().size() == 4);
  
  // Check that the snake didn't change direction
  assert(game.getSnake().direction() == snake::Direction::Up);
  
  // Continue moving up to hit the top wall
  game.setDirection(snake::Direction::Up);
  game.tick();
  game.tick();
  
  // Game should now be over due to wall collision
  assert(game.isGameOver() == true);
  
  // Reset the game
  game.reset();
  
  // After reset, game should be playable again
  assert(game.getScore() == 0);
  assert(game.isGameOver() == false);
  assert(game.getSnake().body().size() == 3);
  assert(game.getFood().has_value());
  
  return 0;
}