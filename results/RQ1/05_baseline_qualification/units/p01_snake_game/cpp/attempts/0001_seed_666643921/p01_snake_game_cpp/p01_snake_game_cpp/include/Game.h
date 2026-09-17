#ifndef SNAKE_GAME_H_
#define SNAKE_GAME_H_

#include "Board.h"
#include "IRandom.h"
#include "Snake.h"
#include "Types.h"

#include <cstddef>
#include <deque>
#include <optional>

namespace snake {

/// Orchestrates the game state, handling ticks, direction changes, collisions, and food placement
class Game {
 public:
  /// Constructs a new Game with the specified dimensions and random number generator
  /// @param width The width of the game board (must be > 0)
  /// @param height The height of the game board (must be > 0)
  /// @param rng A reference to the random number generator to use for food placement
  /// @throws std::invalid_argument if width or height is not greater than 0
  Game(std::size_t width, std::size_t height, IRandom& rng);

  /// Resets the game to its initial state
  void reset();

  /// Sets the desired direction for the snake to move in the next tick
  /// @param d The desired direction
  void setDirection(Direction d);

  /// Advances the game state by one tick
  void tick();

  /// Checks if the game is over
  /// @return true if the game is over, false otherwise
  bool isGameOver() const noexcept;

  /// Gets the current score
  /// @return The current score
  std::size_t getScore() const noexcept;

  /// Gets a const reference to the snake
  /// @return A const reference to the snake
  const Snake& getSnake() const noexcept;

  /// Gets the current food position, if any
  /// @return An optional containing the food position, or std::nullopt if no food is placed
  std::optional<Position> getFood() const;

 private:
  /// Places food on an unoccupied cell using the random number generator
  void placeFood();

  /// Checks if moving to a given position would result in a self-collision
  /// @param next The position to check for potential collision
  /// @param grow Whether the snake will grow after moving to this position
  /// @return true if a self-collision would occur, false otherwise
  bool wouldSelfCollide(Position next, bool grow) const;

  Board board_;
  IRandom& rng_;
  Snake snake_;
  std::optional<Position> food_;
  std::size_t score_;
  bool gameOver_;
  std::optional<Direction> pendingDir_;
};

}  // namespace snake

#endif  // SNAKE_GAME_H_