#ifndef GAME_H
#define GAME_H

#include <vector>
#include <cstdint>
#include "Entities.h"
#include "Geometry.h"

/**
 * @brief Main game orchestrator that manages the game state and tick processing
 */
class Game {
private:
    Arena arena_;
    std::vector<Tank> tanks_;
    std::vector<Projectile> projectiles_;
    std::vector<std::pair<int32_t, Command>> pending_;
    std::vector<int32_t> scores_;
    int32_t tickCount_;
    int32_t winnerId_; // -1 if none

public:
    /**
     * @brief Constructs a game with the specified arena dimensions
     * @param width The width of the arena
     * @param height The height of the arena
     */
    explicit Game(int32_t width, int32_t height);

    /**
     * @brief Resets the game to its initial state
     */
    void reset();

    /**
     * @brief Gets a reference to the game arena
     * @return Reference to the arena
     */
    Arena& arena();

    /**
     * @brief Gets a const reference to the game arena
     * @return Const reference to the arena
     */
    const Arena& arena() const;

    /**
     * @brief Queues a command for a tank
     * @param tankId The ID of the tank
     * @param cmd The command to queue
     * @return True if command was queued successfully, false otherwise
     */
    bool queueCommand(int32_t tankId, Command cmd);

    /**
     * @brief Processes one game tick
     */
    void tick();

    /**
     * @brief Gets a pointer to a tank by ID
     * @param id The ID of the tank
     * @return Pointer to the tank or nullptr if not found
     */
    const Tank* getTank(int32_t id) const;

    /**
     * @brief Gets the score of a tank
     * @param id The ID of the tank
     * @return The score of the tank
     */
    int32_t getScore(int32_t id) const;

    /**
     * @brief Gets the winner ID
     * @return The ID of the winner, or -1 if no winner
     */
    int32_t getWinner() const;

    /**
     * @brief Checks if the game is over
     * @return True if the game is over, false otherwise
     */
    bool isOver() const;

    /**
     * @brief Gets the projectiles in the game
     * @return Const reference to the vector of projectiles
     */
    const std::vector<Projectile>& getProjectiles() const;
};

#endif // GAME_H