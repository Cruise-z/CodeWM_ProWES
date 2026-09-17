#include "Media/MediaMetadata.h"
#include <stdexcept>

namespace Media {

MediaMetadata::MediaMetadata(std::string title, std::int64_t duration_ms)
    : title_(std::move(title)), duration_ms_(duration_ms) {
  if (duration_ms_ < 0) {
    throw std::invalid_argument("Duration cannot be negative");
  }
}

const std::string& MediaMetadata::title() const {
  return title_;
}

std::int64_t MediaMetadata::duration_ms() const {
  return duration_ms_;
}

}  // namespace Media