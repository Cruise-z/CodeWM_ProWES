#include "Game.h"

Game::Game() noexcept 
    : board_(), 
      score_(0), 
      state_(GameState::Ongoing),
      spawner_() {
}

void Game::reset() noexcept {
  board_.clear();
  spawner_.initialFill(board_);
  score_ = 0;
  state_ = GameState::Ongoing;
}

bool Game::move(Move::Direction dir) noexcept {
  auto result = Move::applyMove(board_, dir);
  
  if (!result.moved) {
    return false;
  }
  
  score_ += result.scoreGained;
  
  // Spawn a new tile
  spawner_.spawn(board_);
  
  // Check win condition
  if (board_.maxTile() >= 2048) {
    state_ = GameState::Won;
  } else if (!Move::hasLegalMove(board_)) {
    state_ = GameState::Lost;
  } else {
    state_ = GameState::Ongoing;
  }
  
  return true;
}

const Board& Game::board() const noexcept {
  return board_;
}

std::uint32_t Game::score() const noexcept {
  return score_;
}

GameState Game::state() const noexcept {
  return state_;
}