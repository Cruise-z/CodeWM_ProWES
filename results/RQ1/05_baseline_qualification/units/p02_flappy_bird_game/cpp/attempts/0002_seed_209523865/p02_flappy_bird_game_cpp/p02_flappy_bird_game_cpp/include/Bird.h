#ifndef BIRD_H_
#define BIRD_H_

#include "GameConfig.h"
#include <algorithm>

// Bird entity representing the player character in the game
class Bird {
private:
    double y_;   // Y position of the bird (increases upward)
    double v_;   // Vertical velocity of the bird

public:
    // Constructs a bird at the given initial position and velocity
    Bird(double y0, double v0);

    // Applies a flap impulse to the bird
    void flap(const GameConfig& cfg);

    // Updates the bird's position and velocity based on physics
    void update(double dt, const GameConfig& cfg);

    // Returns the current Y position of the bird
    double y() const noexcept;

    // Returns the current vertical velocity of the bird
    double velocity() const noexcept;

    // Returns the top Y coordinate of the bird
    double top(const GameConfig& cfg) const noexcept;

    // Returns the bottom Y coordinate of the bird
    double bottom(const GameConfig& cfg) const noexcept;

    // Resets the bird to the given Y position
    void reset(double y0) noexcept;
};

#endif // BIRD_H_