#include "Player/Player.h"
#include "Media/MediaMetadata.h"
#include <algorithm>
#include <cassert>

namespace Player {

Player::Player(const Time::IClock& clock)
    : clock_(clock),
      state_(PlaybackState::Stopped),
      current_media_(nullptr),
      position_ms_(0),
      last_tick_ms_(0),
      volume_(50),
      muted_(false) {}

void Player::set_current_media(const Media::MediaMetadata* media) {
  current_media_ = media;
  position_ms_ = 0;
  last_tick_ms_ = clock_.now_ms();
  if (media == nullptr) {
    state_ = PlaybackState::Stopped;
  }
}

const Media::MediaMetadata* Player::current_media() const {
  return current_media_;
}

PlaybackState Player::state() const {
  return state_;
}

std::int64_t Player::position_ms() const {
  return position_ms_;
}

std::int64_t Player::duration_ms() const {
  if (current_media_ == nullptr) {
    return 0;
  }
  return current_media_->duration_ms();
}

bool Player::play() {
  if (current_media_ == nullptr) {
    return false;
  }
  
  if (state_ == PlaybackState::Playing) {
    return true;
  }
  
  if (state_ == PlaybackState::Stopped) {
    position_ms_ = 0;
  }
  
  state_ = PlaybackState::Playing;
  last_tick_ms_ = clock_.now_ms();
  return true;
}

void Player::pause() {
  if (state_ == PlaybackState::Playing) {
    state_ = PlaybackState::Paused;
  }
}

void Player::stop() {
  state_ = PlaybackState::Stopped;
  position_ms_ = 0;
}

void Player::seek(std::int64_t ms) {
  if (current_media_ == nullptr) {
    return;
  }
  
  const auto duration = current_media_->duration_ms();
  position_ms_ = std::clamp(ms, static_cast<std::int64_t>(0), duration);
  
  // If we're at the end, pause the player
  if (position_ms_ >= duration) {
    state_ = PlaybackState::Paused;
  }
}

void Player::update_to_now() {
  if (current_media_ == nullptr || state_ != PlaybackState::Playing) {
    return;
  }
  
  const auto now_ms = clock_.now_ms();
  const auto delta_ms = now_ms - last_tick_ms_;
  last_tick_ms_ = now_ms;
  
  position_ms_ += delta_ms;
  
  // Clamp position to media duration
  const auto duration = current_media_->duration_ms();
  if (position_ms_ >= duration) {
    position_ms_ = duration;
    state_ = PlaybackState::Paused;
  }
}

int Player::set_volume(int v) {
  volume_ = std::clamp(v, 0, 100);
  return volume_;
}

int Player::volume() const {
  return volume_;
}

void Player::mute(bool m) {
  muted_ = m;
}

bool Player::muted() const {
  return muted_;
}

int Player::effective_volume() const {
  return muted_ ? 0 : volume_;
}

}  // namespace Player