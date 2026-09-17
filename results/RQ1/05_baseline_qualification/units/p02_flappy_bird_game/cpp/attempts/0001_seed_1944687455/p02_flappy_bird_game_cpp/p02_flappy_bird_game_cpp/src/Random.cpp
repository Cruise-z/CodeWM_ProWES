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

#include "Random.h"
#include <limits>

namespace {

// LCG constants: a = 6364136223846793005, c = 1
constexpr std::uint64_t kLcgA = 6364136223846793005ULL;
constexpr std::uint64_t kLcgC = 1ULL;

}  // namespace

LcgRandom::LcgRandom(std::uint64_t seed) : state_(seed) {}

std::uint64_t LcgRandom::nextUint64() {
  state_ = kLcgA * state_ + kLcgC;
  return state_;
}

double LcgRandom::nextUnit() {
  return static_cast<double>(nextUint64()) / 
         (static_cast<double>(std::numeric_limits<std::uint64_t>::max()) + 1.0);
}