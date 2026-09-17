#include "Runtime/App.h"
#include "Time/ManualClock.h"
#include "Playlist/Playlist.h"
#include "Media/MediaMetadata.h"
#include "Player/Player.h"
#include <cstdlib>

namespace Runtime {

int App::run_demo() {
  // Create a manual clock starting at 0ms
  Time::ManualClock clock(0);

  // Create a playlist
  Playlist::Playlist playlist;

  // Create some media metadata
  Media::MediaMetadata media1("Video 1", 10000);  // 10 seconds
  Media::MediaMetadata media2("Video 2", 15000);  // 15 seconds

  // Add media to playlist
  playlist.add(media1);
  playlist.add(media2);

  // Select the first item
  playlist.select(0);

  // Create a player with our manual clock
  Player::Player player(clock);

  // Set the current media
  player.set_current_media(playlist.current());

  // Play the media
  player.play();

  // Advance clock by 5000ms (5 seconds)
  clock.advance(5000);

  // Update player to reflect new time
  player.update_to_now();

  // Pause the player
  player.pause();

  // Stop the player
  player.stop();

  // Return success
  return 0;
}

}  // namespace Runtime