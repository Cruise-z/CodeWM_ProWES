#ifndef INCLUDE_PLAYER_PLAYER_H_
#define INCLUDE_PLAYER_PLAYER_H_

#include "Player/PlaybackState.h"
#include "Time/IClock.h"
#include <cstdint>
#include <memory>

namespace Media {
class MediaMetadata;
}  // namespace Media

namespace Player {

/// Core logic for a media player with state transitions, seeking, and time-based advancement.
class Player {
 public:
  /// Constructs a player with the given clock.
  ///
  /// @param clock The clock to use for time tracking.
  explicit Player(const Time::IClock& clock);

  /// Sets the current media item to play.
  ///
  /// @param media The media metadata to set as current, or nullptr to clear.
  void set_current_media(const Media::MediaMetadata* media);

  /// Gets the currently playing media item.
  ///
  /// @return Pointer to the currently playing media metadata, or nullptr if none.
  const Media::MediaMetadata* current_media() const;

  /// Gets the current playback state.
  ///
  /// @return The current playback state.
  PlaybackState state() const;

  /// Gets the current playback position in milliseconds.
  ///
  /// @return The current position in milliseconds.
  std::int64_t position_ms() const;

  /// Gets the duration of the currently playing media in milliseconds.
  ///
  /// @return The duration in milliseconds, or 0 if no media is set.
  std::int64_t duration_ms() const;

  /// Starts playback.
  ///
  /// @return True if playback started successfully, false if already playing or no media set.
  bool play();

  /// Pauses playback.
  void pause();

  /// Stops playback and resets position to 0.
  void stop();

  /// Seeks to the specified position in the current media.
  ///
  /// @param ms The target position in milliseconds.
  void seek(std::int64_t ms);

  /// Updates the player's internal state based on elapsed time from the clock.
  void update_to_now();

  /// Sets the volume level.
  ///
  /// @param v The volume level (0-100).
  /// @return The actual volume level set.
  int set_volume(int v);

  /// Gets the current volume level.
  ///
  /// @return The current volume level.
  int volume() const;

  /// Mutes or unmutes the player.
  ///
  /// @param m True to mute, false to unmute.
  void mute(bool m);

  /// Checks if the player is currently muted.
  ///
  /// @return True if muted, false otherwise.
  bool muted() const;

  /// Gets the effective volume, considering mute status.
  ///
  /// @return The effective volume level (0-100 if not muted, 0 if muted).
  int effective_volume() const;

 private:
  const Time::IClock& clock_;
  PlaybackState state_;
  const Media::MediaMetadata* current_media_;
  std::int64_t position_ms_;
  std::int64_t last_tick_ms_;
  int volume_;
  bool muted_;
};

}  // namespace Player

#endif  // INCLUDE_PLAYER_PLAYER_H_