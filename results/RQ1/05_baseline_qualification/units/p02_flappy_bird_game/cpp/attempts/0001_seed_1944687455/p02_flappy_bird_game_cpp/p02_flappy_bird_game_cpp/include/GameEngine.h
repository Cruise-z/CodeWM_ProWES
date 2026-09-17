#ifndef GAMEENGINE_H
#define GAMEENGINE_H

#include <memory>
#include "GameConfig.h"
#include "GameState.h"
#include "Random.h"

/// @brief GameEngine is the main facade that coordinates the game state, configuration, and random number generation
class GameEngine {
private:
    /// @brief Game configuration constants
    GameConfig cfg_;

    /// @brief Unique pointer to the random number generator
    std::unique_ptr<IRandom> rng_;

    /// @brief Game state management
    GameState state_;

public:
    /// @brief Construct a new GameEngine with given configuration and random number generator
    /// @param cfg Game configuration
    /// @param rng Unique pointer to random number generator
    GameEngine(GameConfig cfg, std::unique_ptr<IRandom> rng);

    /// @brief Reset the game to initial state
    void reset();

    /// @brief Apply flap impulse to the bird if game is not over
    void flap();

    /// @brief Step the game forward by given time delta
    /// @param dt Time step
    void step(double dt);

    /// @brief Get current game score
    /// @return Current score
    int score() const noexcept;

    /// @brief Check if game is over
    /// @return True if game is over
    bool isGameOver() const noexcept;

    /// @brief Get bird's Y position
    /// @return Bird's Y position
    double birdY() const noexcept;

    /// @brief Get reference to vector of pipes
    /// @return Const reference to pipes vector
    const std::vector<Pipe>& pipes() const noexcept;

    /// @brief Get game configuration
    /// @return Const reference to game configuration
    const GameConfig& config() const noexcept;
};

#endif // GAMEENGINE_H