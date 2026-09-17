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