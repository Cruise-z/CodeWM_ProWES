#include "Bird.h"
#include <algorithm>

Bird::Bird(double y0, double v0) : y_(y0), v_(v0) {}

void Bird::flap(const GameConfig& cfg) {
  v_ += cfg.flapImpulse;
}

void Bird::update(double dt, const GameConfig& cfg) {
  // Apply gravity
  v_ -= cfg.gravity * dt;
  
  // Cap the falling speed
  v_ = std::max(v_, -cfg.maxFallSpeed);
  
  // Update position
  y_ += v_ * dt;
  
  // Clamp to world bounds
  y_ = std::clamp(y_, 0.0, cfg.worldHeight);
}

double Bird::y() const noexcept {
  return y_;
}

double Bird::velocity() const noexcept {
  return v_;
}

double Bird::top(const GameConfig& cfg) const noexcept {
  return y_ + cfg.birdHeight / 2.0;
}

double Bird::bottom(const GameConfig& cfg) const noexcept {
  return y_ - cfg.birdHeight / 2.0;
}

void Bird::reset(double y0) noexcept {
  y_ = y0;
  v_ = 0.0;
}