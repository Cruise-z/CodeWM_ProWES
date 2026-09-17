#ifndef SPAWNER_H
#define SPAWNER_H

#include <cstdint>

class Board;

/**
 * @brief Handles deterministic tile spawning for the 2048 game.
 */
class Spawner {
 public:
  /**
   * @brief Spawns a new tile with value 2 in the first empty cell in row-major order.
   * @param board Reference to the board where the tile will be spawned.
   * @return True if a tile was successfully spawned, false if the board is full.
   */
  bool spawn(Board& board) noexcept;

  /**
   * @brief Fills the board with the initial two tiles of value 2.
   * @param board Reference to the board to initialize.
   */
  void initialFill(Board& board) noexcept;
};

#endif // SPAWNER_H