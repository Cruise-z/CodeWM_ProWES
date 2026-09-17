#include "Snake.h"
#include <stdexcept>

namespace snake {

Snake::Snake(Position start, Direction dir, int initialLength) : dir_(dir) {
  if (initialLength <= 0) {
    throw std::invalid_argument("Initial length must be positive");
  }

  // Initialize the snake body with the specified length
  // The body extends in the opposite direction from the initial direction
  switch (dir) {
    case Direction::Up:
      for (int i = 0; i < initialLength; ++i) {
        body_.push_back({start.x, start.y + i});
      }
      break;
    case Direction::Down:
      for (int i = 0; i < initialLength; ++i) {
        body_.push_back({start.x, start.y - i});
      }
      break;
    case Direction::Left:
      for (int i = 0; i < initialLength; ++i) {
        body_.push_back({start.x + i, start.y});
      }
      break;
    case Direction::Right:
      for (int i = 0; i < initialLength; ++i) {
        body_.push_back({start.x - i, start.y});
      }
      break;
  }
}

Position Snake::head() const {
  return body_.front();
}

Position Snake::tail() const {
  return body_.back();
}

const std::deque<Position>& Snake::body() const noexcept {
  return body_;
}

Direction Snake::direction() const noexcept {
  return dir_;
}

bool Snake::trySetDirection(Direction d) {
  // Prevent 180-degree turns
  if ((d == Direction::Up && dir_ == Direction::Down) ||
      (d == Direction::Down && dir_ == Direction::Up) ||
      (d == Direction::Left && dir_ == Direction::Right) ||
      (d == Direction::Right && dir_ == Direction::Left)) {
    return false;
  }
  
  dir_ = d;
  return true;
}

void Snake::advanceTo(Position next, bool grow) {
  // Add new head
  body_.push_front(next);
  
  // Remove tail unless we're growing
  if (!grow) {
    body_.pop_back();
  }
}

bool Snake::occupies(Position p) const noexcept {
  for (const auto& segment : body_) {
    if (segment.x == p.x && segment.y == p.y) {
      return true;
    }
  }
  return false;
}

}  // namespace snake