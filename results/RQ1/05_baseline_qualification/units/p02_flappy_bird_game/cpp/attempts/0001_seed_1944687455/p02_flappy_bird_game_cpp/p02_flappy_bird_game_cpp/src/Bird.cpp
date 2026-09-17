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

#include "Bird.h"
#include <algorithm>

Bird::Bird(double y0, double v0) noexcept : y_(y0), v_(v0) {}

void Bird::flap(const GameConfig& cfg) {
    v_ += cfg.flapImpulse;
}

void Bird::update(double dt, const GameConfig& cfg) {
    // Apply gravity
    v_ -= cfg.gravity * dt;
    
    // Cap fall speed
    v_ = std::max(v_, -cfg.maxFallSpeed);
    
    // Integrate position
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