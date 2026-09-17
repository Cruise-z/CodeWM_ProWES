#ifndef PIPE_H_
#define PIPE_H_

#include "GameConfig.h"
#include <algorithm>

// Pipe entity representing a pipe obstacle in the game
class Pipe {
 public:
  // X coordinate of the pipe's left edge
  double x;
  
  // Y coordinate of the pipe gap center
  double gapY;
  
  // Flag indicating whether the pipe has been scored
  bool scored;

  // Constructs a pipe at the given initial position
  Pipe(double x0, double gapY0);

  // Updates the pipe's position based on game physics
  void update(double dt, const GameConfig& cfg);

  // Checks if the pipe is completely offscreen to the left
  bool isOffscreen(const GameConfig& cfg) const;

  // Checks if the pipe has passed the bird's x position
  bool hasPassedBird(double birdX, const GameConfig& cfg) const;

  // Checks if the bird collides with this pipe
  bool collidesWithBird(double birdX, double birdTop, double birdBottom, 
                        const GameConfig& cfg) const;

 private:
  // Helper method to check if two ranges overlap
  static bool rangesOverlap(double aMin, double aMax, double bMin, double bMax);
};

#endif  // PIPE_H_