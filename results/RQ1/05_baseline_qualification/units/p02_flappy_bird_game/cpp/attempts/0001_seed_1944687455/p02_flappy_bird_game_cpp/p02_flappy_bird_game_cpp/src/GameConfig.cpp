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

#include "GameConfig.h"
#include <stdexcept>

GameConfig GameConfig::Default() {
    GameConfig cfg;
    cfg.worldWidth = 400.0;
    cfg.worldHeight = 600.0;
    cfg.gravity = 500.0;
    cfg.flapImpulse = 200.0;
    cfg.maxFallSpeed = 300.0;
    cfg.pipeSpeed = 150.0;
    cfg.pipeWidth = 50.0;
    cfg.pipeGapHeight = 150.0;
    cfg.pipeSpawnInterval = 1.5;
    cfg.birdX = 80.0;
    cfg.birdWidth = 30.0;
    cfg.birdHeight = 25.0;
    return cfg;
}

void GameConfig::validate() const {
    if (worldWidth <= 0.0 || worldHeight <= 0.0) {
        throw std::invalid_argument("World dimensions must be positive");
    }
    if (gravity <= 0.0) {
        throw std::invalid_argument("Gravity must be positive");
    }
    if (flapImpulse <= 0.0) {
        throw std::invalid_argument("Flap impulse must be positive");
    }
    if (maxFallSpeed <= 0.0) {
        throw std::invalid_argument("Max fall speed must be positive");
    }
    if (pipeSpeed <= 0.0) {
        throw std::invalid_argument("Pipe speed must be positive");
    }
    if (pipeWidth <= 0.0) {
        throw std::invalid_argument("Pipe width must be positive");
    }
    if (pipeGapHeight <= 0.0) {
        throw std::invalid_argument("Pipe gap height must be positive");
    }
    if (pipeGapHeight >= worldHeight) {
        throw std::invalid_argument("Pipe gap height must be less than world height");
    }
    if (pipeSpawnInterval <= 0.0) {
        throw std::invalid_argument("Pipe spawn interval must be positive");
    }
    if (birdX < 0.0 || birdX > worldWidth - birdWidth) {
        throw std::invalid_argument("Bird X position must be within world bounds");
    }
}