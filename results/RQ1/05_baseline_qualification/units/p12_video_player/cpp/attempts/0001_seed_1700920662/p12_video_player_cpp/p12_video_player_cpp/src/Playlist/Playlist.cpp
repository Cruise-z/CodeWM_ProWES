#include "Playlist/Playlist.h"
#include <stdexcept>

namespace Playlist {

void Playlist::add(const Media::MediaMetadata& item) {
  items_.push_back(item);
}

std::size_t Playlist::size() const {
  return items_.size();
}

const Media::MediaMetadata* Playlist::get(std::size_t index) const {
  if (index >= items_.size()) {
    return nullptr;
  }
  return &items_[index];
}

const Media::MediaMetadata* Playlist::current() const {
  if (current_index_ < 0 || static_cast<std::size_t>(current_index_) >= items_.size()) {
    return nullptr;
  }
  return &items_[current_index_];
}

int Playlist::current_index() const {
  return current_index_;
}

bool Playlist::select(std::size_t index) {
  if (index >= items_.size()) {
    return false;
  }
  current_index_ = static_cast<int>(index);
  return true;
}

bool Playlist::next() {
  if (current_index_ < 0) {
    return false;
  }
  if (static_cast<std::size_t>(current_index_) >= items_.size() - 1) {
    return false;
  }
  ++current_index_;
  return true;
}

bool Playlist::prev() {
  if (current_index_ <= 0) {
    return false;
  }
  --current_index_;
  return true;
}

}  // namespace Playlist