/*
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "Pipe.h"
#include <algorithm>

Pipe::Pipe(double x0, double gapY0) noexcept 
    : x(x0), gapY(gapY0), scored(false) {}

void Pipe::update(double dt, const GameConfig& cfg) {
    // Move pipe leftward at pipe speed
    x -= cfg.pipeSpeed * dt;
}

bool Pipe::isOffscreen(const GameConfig& cfg) const {
    // Pipe is offscreen if it's completely to the left of the screen
    return x + cfg.pipeWidth < 0.0;
}

bool Pipe::hasPassedBird(double birdX, const GameConfig& cfg) const {
    // Bird has passed the pipe if the pipe's right edge is to the left of the bird
    return x + cfg.pipeWidth < birdX;
}

bool Pipe::collidesWithBird(double birdX, double birdTop, double birdBottom, 
                           const GameConfig& cfg) const {
    // Check horizontal overlap between bird and pipe
    if (birdX + cfg.birdWidth/2.0 < x || birdX - cfg.birdWidth/2.0 > x + cfg.pipeWidth) {
        return false;
    }
    
    // Check vertical overlap, excluding the gap
    // Bird is above the pipe gap
    if (birdBottom > gapY + cfg.pipeGapHeight/2.0) {
        return true;
    }
    
    // Bird is below the pipe gap
    if (birdTop < gapY - cfg.pipeGapHeight/2.0) {
        return true;
    }
    
    // Bird is within the gap, no collision
    return false;
}