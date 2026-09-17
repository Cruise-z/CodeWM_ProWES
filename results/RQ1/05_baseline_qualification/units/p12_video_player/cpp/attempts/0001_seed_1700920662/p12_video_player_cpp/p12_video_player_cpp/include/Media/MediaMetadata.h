#ifndef INCLUDE_MEDIA_MEDIAMETADATA_H_
#define INCLUDE_MEDIA_MEDIAMETADATA_H_

#include <cstdint>
#include <string>

namespace Media {

/// Represents metadata for a media item including title and duration.
class MediaMetadata {
 public:
  /// Constructs media metadata with the given title and duration.
  ///
  /// @param title The title of the media item.
  /// @param duration_ms The duration of the media item in milliseconds.
  /// @throws std::invalid_argument if duration_ms is negative.
  MediaMetadata(std::string title, std::int64_t duration_ms);

  /// Gets the title of the media item.
  ///
  /// @return The title of the media item.
  const std::string& title() const;

  /// Gets the duration of the media item in milliseconds.
  ///
  /// @return The duration of the media item in milliseconds.
  std::int64_t duration_ms() const;

 private:
  std::string title_;
  std::int64_t duration_ms_;
};

}  // namespace Media

#endif  // INCLUDE_MEDIA_MEDIAMETADATA_H_