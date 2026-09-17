#ifndef PIPE_H_
#define PIPE_H_

#include "GameConfig.h"
#include <algorithm>

// Pipe entity representing obstacles in the game
class Pipe {
public:
    double x;           // X position of the pipe
    double gapY;        // Y position of the center of the gap
    bool scored;        // Flag indicating if the bird has passed this pipe

    // Constructs a pipe at the given initial position
    Pipe(double x0, double gapY0);

    // Updates the pipe's position based on game physics
    void update(double dt, const GameConfig& cfg);

    // Checks if the pipe is off the left side of the screen
    bool isOffscreen(const GameConfig& cfg) const;

    // Checks if the bird has passed this pipe
    bool hasPassedBird(double birdX, const GameConfig& cfg) const;

    // Checks if the bird collides with this pipe
    bool collidesWithBird(double birdX, double birdTop, double birdBottom, const GameConfig& cfg) const;
};

#endif // PIPE_H_