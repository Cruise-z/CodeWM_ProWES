#ifndef GAME_H
#define GAME_H

#include "Board.h"
#include "Move.h"
#include "Spawner.h"
#include <cstdint>

/**
 * @brief Represents the game state for 2048.
 */
enum class GameState {
  Ongoing,
  Won,
  Lost
};

/**
 * @brief Main game class that orchestrates the 2048 game logic.
 */
class Game {
 public:
  /**
   * @brief Constructs a new Game object.
   */
  Game() noexcept;

  /**
   * @brief Resets the game to its initial state.
   */
  void reset() noexcept;

  /**
   * @brief Attempts to move tiles in the specified direction.
   * @param dir Direction of the move.
   * @return True if the move was successful (tiles moved), false otherwise.
   */
  bool move(Move::Direction dir) noexcept;

  /**
   * @brief Gets a constant reference to the game board.
   * @return Constant reference to the board.
   */
  const Board& board() const noexcept;

  /**
   * @brief Gets the current score.
   * @return Current score.
   */
  std::uint32_t score() const noexcept;

  /**
   * @brief Gets the current game state.
   * @return Current game state.
   */
  GameState state() const noexcept;

 private:
  Board board_;
  std::uint32_t score_;
  GameState state_;
  Spawner spawner_;
};

#endif // GAME_H