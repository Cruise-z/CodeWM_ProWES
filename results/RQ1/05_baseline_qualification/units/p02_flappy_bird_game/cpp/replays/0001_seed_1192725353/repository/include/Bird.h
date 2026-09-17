#ifndef BIRD_H_
#define BIRD_H_

#include "GameConfig.h"
#include <algorithm>

// Bird entity representing the flappy bird in the game
class Bird {
 public:
  // Constructs a bird at the given initial position and velocity
  Bird(double y0, double v0);

  // Applies a flap impulse to the bird
  void flap(const GameConfig& cfg);

  // Updates the bird's position and velocity based on physics
  void update(double dt, const GameConfig& cfg);

  // Returns the current y position of the bird
  double y() const noexcept;

  // Returns the current vertical velocity of the bird
  double velocity() const noexcept;

  // Returns the top edge of the bird's bounding box
  double top(const GameConfig& cfg) const noexcept;

  // Returns the bottom edge of the bird's bounding box
  double bottom(const GameConfig& cfg) const noexcept;

  // Resets the bird to a specified y position
  void reset(double y0) noexcept;

 private:
  double y_;  // Current y position
  double v_;  // Current vertical velocity
};

#endif  // BIRD_H_