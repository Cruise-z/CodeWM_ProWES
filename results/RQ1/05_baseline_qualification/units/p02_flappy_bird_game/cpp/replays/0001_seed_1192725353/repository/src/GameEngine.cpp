#include "GameEngine.h"
#include <utility>

GameEngine::GameEngine(GameConfig cfg, std::unique_ptr<IRandom> rng)
    : cfg_(std::move(cfg)), rng_(std::move(rng)), state_(cfg_) {
  cfg_.validate();
}

void GameEngine::reset() {
  state_.reset();
}

void GameEngine::flap() {
  state_.flap();
}

void GameEngine::step(double dt) {
  state_.update(dt, *rng_);
}

int GameEngine::score() const noexcept {
  return state_.score();
}

bool GameEngine::isGameOver() const noexcept {
  return state_.gameOver();
}

double GameEngine::birdY() const noexcept {
  return state_.birdY();
}

const std::vector<Pipe>& GameEngine::pipes() const noexcept {
  return state_.pipes();
}

const GameConfig& GameEngine::config() const noexcept {
  return cfg_;
}