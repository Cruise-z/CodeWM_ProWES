#include "GameState.h"
#include "Random.h"
#include <algorithm>

GameState::GameState(GameConfig cfg) 
    : cfg_(cfg),
      bird_(cfg.worldHeight / 2.0, 0.0),
      pipes_(),
      score_(0),
      gameOver_(false),
      timeSinceLastPipe_(0.0) {
  cfg_.validate();
}

void GameState::reset() {
  bird_.reset(cfg_.worldHeight / 2.0);
  pipes_.clear();
  score_ = 0;
  gameOver_ = false;
  timeSinceLastPipe_ = 0.0;
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
  if (bird_.y() <= 0 || bird_.y() >= cfg_.worldHeight) {
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
    // Generate gap position within playable area
    double gapY = rng.nextUnit() * (cfg_.worldHeight - cfg_.pipeGapHeight);
    // Ensure gap stays within world bounds
    gapY = std::clamp(gapY, cfg_.pipeGapHeight / 2.0, cfg_.worldHeight - cfg_.pipeGapHeight / 2.0);
    
    pipes_.emplace_back(cfg_.worldWidth, gapY);
    timeSinceLastPipe_ = 0.0;
  }

  // Check for collisions and scoring
  double birdTop = bird_.top(cfg_);
  double birdBottom = bird_.bottom(cfg_);
  double birdX = cfg_.birdX;
  
  for (auto& pipe : pipes_) {
    // Score when pipe passes bird
    if (!pipe.scored && pipe.hasPassedBird(birdX, cfg_)) {
      pipe.scored = true;
      score_++;
    }
    
    // Check collision with pipe
    if (pipe.collidesWithBird(birdX, birdTop, birdBottom, cfg_)) {
      gameOver_ = true;
      return;
    }
  }
  
  // Remove offscreen pipes
  pipes_.erase(
    std::remove_if(pipes_.begin(), pipes_.end(),
      [&cfg = cfg_](const Pipe& p) { return p.isOffscreen(cfg); }),
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