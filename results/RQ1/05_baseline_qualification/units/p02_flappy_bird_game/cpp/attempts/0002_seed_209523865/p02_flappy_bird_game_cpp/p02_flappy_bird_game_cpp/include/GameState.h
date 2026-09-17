#ifndef GAMESTATE_H_
#define GAMESTATE_H_

#include <vector>
#include "Bird.h"
#include "Pipe.h"
#include "GameConfig.h"
#include <algorithm>

// Forward declaration of IRandom to avoid including its header
class IRandom;

// GameState orchestrates the main game logic, managing the bird, pipes, score, and game over state
class GameState {
private:
    GameConfig cfg_;                           // Game configuration
    Bird bird_;                                // Bird entity
    std::vector<Pipe> pipes_;                  // Vector of pipe entities
    int score_;                                // Current game score
    bool gameOver_;                            // Flag indicating if the game is over
    double timeSinceLastPipe_;                 // Time since last pipe was spawned

public:
    // Constructs a new game state with the given configuration
    explicit GameState(GameConfig cfg);

    // Resets the game state to its initial conditions
    void reset();

    // Makes the bird flap if the game is not over
    void flap();

    // Updates the game state by the given time delta
    void update(double dt, IRandom& rng);

    // Returns the current score
    int score() const noexcept;

    // Returns whether the game is over
    bool gameOver() const noexcept;

    // Returns a const reference to the vector of pipes
    const std::vector<Pipe>& pipes() const noexcept;

    // Returns the current Y position of the bird
    double birdY() const noexcept;

    // Returns the top Y coordinate of the bird
    double birdTop() const noexcept;

    // Returns the bottom Y coordinate of the bird
    double birdBottom() const noexcept;
};

#endif // GAMESTATE_H_