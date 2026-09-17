#ifndef INCLUDE_PLAYER_PLAYBACKSTATE_H_
#define INCLUDE_PLAYER_PLAYBACKSTATE_H_

namespace Player {

/// Enum class representing the playback state of a media player.
enum class PlaybackState {
  Stopped,  ///< Playback is stopped.
  Paused,   ///< Playback is paused.
  Playing   ///< Playback is currently playing.
};

}  // namespace Player

#endif  // INCLUDE_PLAYER_PLAYBACKSTATE_H_