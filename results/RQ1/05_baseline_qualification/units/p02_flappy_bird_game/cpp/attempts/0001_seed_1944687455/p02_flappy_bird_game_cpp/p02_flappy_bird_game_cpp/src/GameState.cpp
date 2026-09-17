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

#include "GameState.h"
#include <algorithm>
#include <stdexcept>

GameState::GameState(GameConfig cfg) 
    : cfg_(std::move(cfg)), 
      bird_(cfg_.worldHeight / 2.0, 0.0),
      score_(0),
      gameOver_(false),
      timeSinceLastPipe_(0.0) {
}

void GameState::reset() {
    pipes_.clear();
    score_ = 0;
    gameOver_ = false;
    timeSinceLastPipe_ = 0.0;
    bird_.reset(cfg_.worldHeight / 2.0);
}

void GameState::flap() {
    if (!gameOver_) {
        bird_.flap(cfg_);
    }
}

void GameState::update(double dt, IRandom& rng) {
    if (gameOver_) {
        return;
    }

    // Update bird
    bird_.update(dt, cfg_);

    // Check for boundary collisions (top or bottom)
    if (bird_.y() <= 0.0 || bird_.y() >= cfg_.worldHeight) {
        gameOver_ = true;
        return;
    }

    // Update pipes
    for (auto& pipe : pipes_) {
        pipe.update(dt, cfg_);
    }

    // Spawn new pipes
    timeSinceLastPipe_ += dt;
    if (timeSinceLastPipe_ >= cfg_.pipeSpawnInterval) {
        // Generate gapY within playable area
        const double minGapY = cfg_.pipeGapHeight / 2.0;
        const double maxGapY = cfg_.worldHeight - cfg_.pipeGapHeight / 2.0;
        const double gapY = minGapY + rng.nextUnit() * (maxGapY - minGapY);
        
        pipes_.emplace_back(cfg_.worldWidth, gapY);
        timeSinceLastPipe_ = 0.0;
    }

    // Check for collisions with pipes
    const double birdTop = bird_.top(cfg_);
    const double birdBottom = bird_.bottom(cfg_);
    for (const auto& pipe : pipes_) {
        if (pipe.collidesWithBird(cfg_.birdX, birdTop, birdBottom, cfg_)) {
            gameOver_ = true;
            return;
        }
        
        // Score when bird passes a pipe
        if (!pipe.scored && pipe.hasPassedBird(cfg_.birdX, cfg_)) {
            pipe.scored = true;
            score_++;
        }
    }

    // Remove offscreen pipes
    pipes_.erase(
        std::remove_if(pipes_.begin(), pipes_.end(),
            [this](const Pipe& pipe) { return pipe.isOffscreen(cfg_); }),
        pipes_.end()
    );
}

int GameState::score() const noexcept {
    return score_;
}

bool GameState::gameOver() const noexcept {
    return gameOver_;
}

const std::vector<Pipe>& GameState::pipes() const noexcept {
    return pipes_;
}

double GameState::birdY() const noexcept {
    return bird_.y();
}

double GameState::birdTop() const noexcept {
    return bird_.top(cfg_);
}

double GameState::birdBottom() const noexcept {
    return bird_.bottom(cfg_);
}