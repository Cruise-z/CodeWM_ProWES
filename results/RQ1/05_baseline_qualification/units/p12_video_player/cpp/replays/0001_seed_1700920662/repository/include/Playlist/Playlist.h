#ifndef INCLUDE_PLAYLIST_PLAYLIST_H_
#define INCLUDE_PLAYLIST_PLAYLIST_H_

#include <vector>
#include <cstddef>
#include "Media/MediaMetadata.h"

namespace Playlist {

/// A playlist container that holds media metadata and supports navigation.
class Playlist {
 public:
  /// Constructs an empty playlist.
  Playlist() = default;

  /// Adds a media item to the playlist.
  ///
  /// @param item The media metadata to add.
  void add(const Media::MediaMetadata& item);

  /// Gets the number of items in the playlist.
  ///
  /// @return The number of items in the playlist.
  std::size_t size() const;

  /// Gets a media item at the specified index.
  ///
  /// @param index The index of the item to retrieve.
  /// @return Pointer to the media metadata at the index, or nullptr if index is out of bounds.
  const Media::MediaMetadata* get(std::size_t index) const;

  /// Gets the currently selected media item.
  ///
  /// @return Pointer to the currently selected media metadata, or nullptr if none is selected.
  const Media::MediaMetadata* current() const;

  /// Gets the index of the currently selected item.
  ///
  /// @return The index of the currently selected item, or -1 if none is selected.
  int current_index() const;

  /// Selects the item at the specified index.
  ///
  /// @param index The index of the item to select.
  /// @return True if the selection was successful, false otherwise.
  bool select(std::size_t index);

  /// Moves to the next item in the playlist.
  ///
  /// @return True if the operation was successful, false if at the end of the playlist.
  bool next();

  /// Moves to the previous item in the playlist.
  ///
  /// @return True if the operation was successful, false if at the beginning of the playlist.
  bool prev();

 private:
  std::vector<Media::MediaMetadata> items_;
  int current_index_ = -1;  // Default to -1 indicating no selection
};

}  // namespace Playlist

#endif  // INCLUDE_PLAYLIST_PLAYLIST_H_