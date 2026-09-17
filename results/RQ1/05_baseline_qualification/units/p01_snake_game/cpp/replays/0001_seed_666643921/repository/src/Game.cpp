#include "Game.h"
#include <stdexcept>

namespace snake {

Game::Game(std::size_t width, std::size_t height, IRandom& rng)
    : board_(width, height),
      rng_(rng),
      snake_(Position{static_cast<int>(width / 2), static_cast<int>(height / 2)}, 
             Direction::Right, 3),
      food_(std::nullopt),
      score_(0),
      gameOver_(false),
      pendingDir_(std::nullopt) {
  if (width == 0 || height == 0) {
    throw std::invalid_argument("Board dimensions must be greater than 0");
  }
  placeFood();
}

void Game::reset() {
  snake_ = Snake(Position{static_cast<int>(board_.getWidth() / 2), 
                         static_cast<int>(board_.getHeight() / 2)}, 
                Direction::Right, 3);
  score_ = 0;
  gameOver_ = false;
  pendingDir_ = std::nullopt;
  food_ = std::nullopt;
  placeFood();
}

void Game::setDirection(Direction d) {
  pendingDir_ = d;
}

void Game::tick() {
  if (gameOver_) {
    return;
  }

  // Apply pending direction change
  if (pendingDir_.has_value()) {
    snake_.trySetDirection(pendingDir_.value());
    pendingDir_ = std::nullopt;
  }

  // Compute next head position based on current direction
  Position next = snake_.head();
  switch (snake_.direction()) {
    case Direction::Up:
      next.y--;
      break;
    case Direction::Down:
      next.y++;
      break;
    case Direction::Left:
      next.x--;
      break;
    case Direction::Right:
      next.x++;
      break;
  }

  // Check if next position is within bounds
  if (!board_.inBounds(next)) {
    gameOver_ = true;
    return;
  }

  // Check for self-collision (allowing move into tail only if not growing)
  bool grow = false;
  if (food_.has_value() && next.x == food_.value().x && next.y == food_.value().y) {
    grow = true;
    score_++;
  }

  if (wouldSelfCollide(next, grow)) {
    gameOver_ = true;
    return;
  }

  // Move snake
  snake_.advanceTo(next, grow);

  // If we ate food, place new food
  if (grow) {
    food_ = std::nullopt;
    placeFood();
  }
}

bool Game::isGameOver() const noexcept {
  return gameOver_;
}

std::size_t Game::getScore() const noexcept {
  return score_;
}

const Snake& Game::getSnake() const noexcept {
  return snake_;
}

std::optional<Position> Game::getFood() const {
  return food_;
}

void Game::placeFood() {
  // Find all empty cells
  std::vector<Position> emptyCells;
  for (std::size_t y = 0; y < board_.getHeight(); ++y) {
    for (std::size_t x = 0; x < board_.getWidth(); ++x) {
      Position p{static_cast<int>(x), static_cast<int>(y)};
      if (!snake_.occupies(p)) {
        emptyCells.push_back(p);
      }
    }
  }

  // If no empty cells, game is over
  if (emptyCells.empty()) {
    gameOver_ = true;
    return;
  }

  // Select a random empty cell
  std::size_t index = rng_.next(emptyCells.size());
  food_ = emptyCells[index];
}

bool Game::wouldSelfCollide(Position next, bool grow) const {
  // Check if next position is occupied by snake body (excluding tail if not growing)
  if (grow) {
    // When growing, we don't remove the tail, so check all body segments
    return snake_.occupies(next);
  } else {
    // When not growing, we remove the tail, so skip tail in collision check
    auto body = snake_.body();
    if (body.size() < 2) {
      return false;
    }
    
    // Skip the tail (last element) when checking for collision
    for (auto it = body.begin(); it != body.end() - 1; ++it) {
      if (it->x == next.x && it->y == next.y) {
        return true;
      }
    }
    return false;
  }
}

}  // namespace snake