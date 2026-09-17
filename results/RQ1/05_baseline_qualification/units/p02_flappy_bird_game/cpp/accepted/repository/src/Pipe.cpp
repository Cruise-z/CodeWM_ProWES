#include "Pipe.h"
#include <algorithm>

Pipe::Pipe(double x0, double gapY0) : x(x0), gapY(gapY0), scored(false) {}

void Pipe::update(double dt, const GameConfig& cfg) {
  // Move the pipe to the left
  x -= cfg.pipeSpeed * dt;
}

bool Pipe::isOffscreen(const GameConfig& cfg) const {
  // Pipe is offscreen if it's completely to the left of the screen
  return x + cfg.pipeWidth < 0;
}

bool Pipe::hasPassedBird(double birdX, const GameConfig& cfg) const {
  // Pipe has passed the bird if the pipe's right edge is behind the bird's position
  return x + cfg.pipeWidth < birdX;
}

bool Pipe::collidesWithBird(double birdX, double birdTop, double birdBottom, 
                            const GameConfig& cfg) const {
  // Check if bird's x position overlaps with pipe's x range
  if (!rangesOverlap(x, x + cfg.pipeWidth, birdX - cfg.birdWidth/2, birdX + cfg.birdWidth/2)) {
    return false;
  }
  
  // Check if bird's y position overlaps with pipe's gap
  double gapTop = gapY + cfg.pipeGapHeight / 2;
  double gapBottom = gapY - cfg.pipeGapHeight / 2;
  
  // Collision occurs if bird is not within the gap
  return !(birdBottom <= gapTop && birdTop >= gapBottom);
}

bool Pipe::rangesOverlap(double aMin, double aMax, double bMin, double bMax) {
  return aMin <= bMax && bMin <= aMax;
}