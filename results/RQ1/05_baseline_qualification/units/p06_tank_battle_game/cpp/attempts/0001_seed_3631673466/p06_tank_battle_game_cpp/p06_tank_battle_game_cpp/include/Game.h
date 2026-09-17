#ifndef GAME_H
#define GAME_H

#include <vector>
#include "Entities.h"

/**
 * @brief Main game orchestrator that manages the game state and tick execution
 */
class Game {
private:
    Arena arena_;
    std::vector<Tank> tanks_;
    std::vector<Projectile> projectiles_;
    std::vector<std::pair<int, Command>> pending_;
    std::vector<int> scores_;
    int tickCount_;
    int winnerId_; // -1 if none

public:
    /**
     * @brief Construct a new Game object
     * @param width The width of the arena
     * @param height The height of the arena
     */
    Game(int width, int height);

    /**
     * @brief Reset the game to its initial state
     */
    void reset();

    /**
     * @brief Get a reference to the arena
     * @return Reference to the arena
     */
    Arena& arena();

    /**
     * @brief Get a const reference to the arena
     * @return Const reference to the arena
     */
    const Arena& arena() const;

    /**
     * @brief Queue a command for a tank
     * @param tankId The ID of the tank
     * @param cmd The command to queue
     * @return true if command was queued, false otherwise
     */
    bool queueCommand(int tankId, Command cmd);

    /**
     * @brief Execute one game tick
     */
    void tick();

    /**
     * @brief Get a const pointer to a tank by ID
     * @param id The ID of the tank
     * @return Const pointer to the tank, or nullptr if not found
     */
    const Tank* getTank(int id) const;

    /**
     * @brief Get the score of a tank
     * @param id The ID of the tank
     * @return The score of the tank
     */
    int getScore(int id) const;

    /**
     * @brief Get the winner ID
     * @return The ID of the winner, or -1 if no winner yet
     */
    int getWinner() const;

    /**
     * @brief Check if the game is over
     * @return true if the game is over, false otherwise
     */
    bool isOver() const;

    /**
     * @brief Get the projectiles
     * @return Const reference to the projectiles vector
     */
    const std::vector<Projectile>& getProjectiles() const;
};

#endif // GAME_H