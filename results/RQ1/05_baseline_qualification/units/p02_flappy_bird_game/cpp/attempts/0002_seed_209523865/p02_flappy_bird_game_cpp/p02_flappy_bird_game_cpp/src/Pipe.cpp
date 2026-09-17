#include "Pipe.h"
#include <algorithm>

Pipe::Pipe(double x0, double gapY0) : x(x0), gapY(gapY0), scored(false) {}

void Pipe::update(double dt, const GameConfig& cfg) {
    // Move the pipe to the left
    x -= cfg.pipeSpeed * dt;
}

bool Pipe::isOffscreen(const GameConfig& cfg) const {
    // Check if the pipe is completely off the left side of the screen
    return x + cfg.pipeWidth < 0.0;
}

bool Pipe::hasPassedBird(double birdX, const GameConfig& cfg) const {
    // Check if the bird has passed this pipe
    return x + cfg.pipeWidth < birdX;
}

bool Pipe::collidesWithBird(double birdX, double birdTop, double birdBottom, const GameConfig& cfg) const {
    // Check if the bird's x position overlaps with the pipe's x range
    if (birdX + cfg.birdWidth / 2.0 > x && birdX - cfg.birdWidth / 2.0 < x + cfg.pipeWidth) {
        // Check if the bird's y position is outside the gap
        double gapTop = gapY + cfg.pipeGapHeight / 2.0;
        double gapBottom = gapY - cfg.pipeGapHeight / 2.0;
        
        // Collision occurs if bird is above the gap top or below the gap bottom
        return birdBottom > gapTop || birdTop < gapBottom;
    }
    
    // No horizontal overlap, so no collision
    return false;
}