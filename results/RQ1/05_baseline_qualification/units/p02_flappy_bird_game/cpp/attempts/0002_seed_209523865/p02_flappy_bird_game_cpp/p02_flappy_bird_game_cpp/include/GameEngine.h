#ifndef GAMEENGINE_H_
#define GAMEENGINE_H_

#include <memory>
#include "GameConfig.h"
#include "GameState.h"
#include "Random.h"

// GameEngine is the main facade that orchestrates the game state and provides
// a simple interface for controlling the game simulation.
class GameEngine {
private:
    GameConfig cfg_;
    std::unique_ptr<IRandom> rng_;
    GameState state_;

public:
    // Constructs a new game engine with the given configuration and random number generator.
    // The configuration is validated in the constructor.
    GameEngine(GameConfig cfg, std::unique_ptr<IRandom> rng);

    // Resets the game to its initial state, preserving the random number generator state.
    void reset();

    // Makes the bird flap if the game is not over.
    void flap();

    // Advances the game state by the given time delta.
    // This method delegates to GameState::update with the provided random number generator.
    void step(double dt);

    // Returns the current score.
    int score() const noexcept;

    // Returns whether the game is over.
    bool isGameOver() const noexcept;

    // Returns the current Y position of the bird.
    double birdY() const noexcept;

    // Returns a const reference to the vector of pipes.
    const std::vector<Pipe>& pipes() const noexcept;

    // Returns a const reference to the game configuration.
    const GameConfig& config() const noexcept;
};

#endif // GAMEENGINE_H_