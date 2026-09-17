#include "GameState.h"
#include "Random.h"
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

    // Check for boundary collisions (top and bottom)
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
        double gapY = rng.nextUnit() * (cfg_.worldHeight - cfg_.pipeGapHeight);
        // Ensure gapY doesn't go out of bounds
        gapY = std::clamp(gapY, cfg_.pipeGapHeight / 2.0, cfg_.worldHeight - cfg_.pipeGapHeight / 2.0);
        
        pipes_.emplace_back(cfg_.worldWidth, gapY);
        timeSinceLastPipe_ = 0.0;
    }

    // Check for collisions and scoring
    double birdTop = bird_.top(cfg_);
    double birdBottom = bird_.bottom(cfg_);
    
    for (auto& pipe : pipes_) {
        // Score when bird passes pipe
        if (!pipe.scored && pipe.hasPassedBird(cfg_.birdX, cfg_)) {
            score_++;
            pipe.scored = true;
        }
        
        // Check collision with pipe
        if (pipe.collidesWithBird(cfg_.birdX, birdTop, birdBottom, cfg_)) {
            gameOver_ = true;
            return;
        }
    }

    // Remove offscreen pipes
    pipes_.erase(
        std::remove_if(pipes_.begin(), pipes_.end(),
            [&](const Pipe& p) { return p.isOffscreen(cfg_); }),
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