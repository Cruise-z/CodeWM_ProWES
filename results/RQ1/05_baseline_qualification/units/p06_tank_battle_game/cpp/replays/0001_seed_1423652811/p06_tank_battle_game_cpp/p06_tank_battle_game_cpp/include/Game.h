#ifndef GAME_H
#define GAME_H

#include <vector>
#include "Entities.h"

/**
 * @brief Main game class orchestrating the battle between tanks.
 * 
 * This class manages the game state including the arena, tanks, projectiles,
 * commands, scores, and winner determination. It provides a deterministic
 * tick-based simulation of the game.
 */
class Game {
private:
    Arena arena_;              ///< The game arena
    std::vector<Tank> tanks_;  ///< Vector of tanks in the game
    std::vector<Projectile> projectiles_;  ///< Vector of active projectiles
    std::vector<std::pair<int, Command>> pending_;  ///< Pending commands to be processed
    std::vector<int> scores_;  ///< Scores for each tank
    int tickCount_;            ///< Current tick count
    int winnerId_;             ///< ID of the winning tank (-1 if no winner)

public:
    /**
     * @brief Constructs a game with specified arena dimensions.
     * @param width Width of the arena
     * @param height Height of the arena
     */
    Game(int width, int height);

    /**
     * @brief Resets the game to initial state.
     * 
     * Clears all entities, resets scores, and initializes tanks at default positions.
     */
    void reset();

    /**
     * @brief Gets a reference to the game arena.
     * @return Reference to the arena
     */
    Arena& arena();

    /**
     * @brief Gets a const reference to the game arena.
     * @return Const reference to the arena
     */
    const Arena& arena() const;

    /**
     * @brief Queues a command for a tank.
     * @param tankId ID of the tank
     * @param cmd Command to queue
     * @return True if command was queued successfully, false otherwise
     */
    bool queueCommand(int tankId, Command cmd);

    /**
     * @brief Executes one game tick.
     * 
     * Processes pending commands, moves projectiles, resolves collisions,
     * updates scores, and determines winner.
     */
    void tick();

    /**
     * @brief Gets a pointer to a tank by ID.
     * @param id Tank ID
     * @return Pointer to the tank if found, nullptr otherwise
     */
    const Tank* getTank(int id) const;

    /**
     * @brief Gets the score of a tank.
     * @param id Tank ID
     * @return Score of the tank
     */
    int getScore(int id) const;

    /**
     * @brief Gets the ID of the winning tank.
     * @return ID of the winning tank, or -1 if no winner
     */
    int getWinner() const;

    /**
     * @brief Checks if the game is over.
     * @return True if game is over, false otherwise
     */
    bool isOver() const;

    /**
     * @brief Gets the vector of active projectiles.
     * @return Const reference to the projectiles vector
     */
    const std::vector<Projectile>& getProjectiles() const;
};

#endif // GAME_H