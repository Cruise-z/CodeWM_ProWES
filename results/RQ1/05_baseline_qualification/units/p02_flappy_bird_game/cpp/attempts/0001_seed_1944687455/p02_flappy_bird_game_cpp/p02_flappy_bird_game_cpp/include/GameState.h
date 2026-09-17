#ifndef GAMESTATE_H
#define GAMESTATE_H

#include <vector>
#include <memory>
#include "Bird.h"
#include "Pipe.h"
#include "GameConfig.h"

/// @brief Forward declaration of IRandom interface
class IRandom;

/// @brief GameState orchestrates the game loop, managing bird, pipes, score, and game over state
class GameState {
private:
    /// @brief Game configuration constants
    GameConfig cfg_;

    /// @brief Bird entity
    Bird bird_;

    /// @brief Vector of active pipes
    std::vector<Pipe> pipes_;

    /// @brief Current game score
    int score_;

    /// @brief Flag indicating if the game is over
    bool gameOver_;

    /// @brief Timer for pipe spawning
    double timeSinceLastPipe_;

public:
    /// @brief Construct a new GameState with given configuration
    /// @param cfg Game configuration
    explicit GameState(GameConfig cfg);

    /// @brief Reset the game state to initial conditions
    void reset();

    /// @brief Apply flap impulse to the bird if game is not over
    void flap();

    /// @brief Update game state for one time step
    /// @param dt Time step
    /// @param rng Random number generator for pipe placement
    void update(double dt, IRandom& rng);

    /// @brief Get current game score
    /// @return Current score
    int score() const noexcept;

    /// @brief Check if game is over
    /// @return True if game is over
    bool gameOver() const noexcept;

    /// @brief Get reference to vector of pipes
    /// @return Const reference to pipes vector
    const std::vector<Pipe>& pipes() const noexcept;

    /// @brief Get bird's Y position
    /// @return Bird's Y position
    double birdY() const noexcept;

    /// @brief Get bird's top edge position
    /// @return Bird's top edge position
    double birdTop() const noexcept;

    /// @brief Get bird's bottom edge position
    /// @return Bird's bottom edge position
    double birdBottom() const noexcept;
};

#endif // GAMESTATE_H