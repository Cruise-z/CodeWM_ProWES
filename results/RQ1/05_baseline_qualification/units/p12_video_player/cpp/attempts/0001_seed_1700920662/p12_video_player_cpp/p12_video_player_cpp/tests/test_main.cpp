#include <cassert>
#include <stdexcept>
#include "Time/ManualClock.h"
#include "Media/MediaMetadata.h"
#include "Playlist/Playlist.h"
#include "Player/Player.h"
#include "Runtime/App.h"

int main() {
  // Test 1: MediaMetadata negative duration throws std::invalid_argument
  try {
    Media::MediaMetadata bad_metadata("Bad Video", -1000);
    assert(false && "Should have thrown std::invalid_argument");
  } catch (const std::invalid_argument&) {
    // Expected
  }

  // Test 2: Player::update_to_now deterministic advancement with ManualClock
  Time::ManualClock clock(0);
  Playlist::Playlist playlist;
  Media::MediaMetadata media("Test Video", 10000);  // 10 seconds
  playlist.add(media);
  playlist.select(0);

  Player::Player player(clock);
  player.set_current_media(playlist.current());
  player.play();

  // Advance clock by 3000ms
  clock.advance(3000);
  player.update_to_now();

  assert(player.position_ms() == 3000);
  assert(player.state() == Player::PlaybackState::Playing);

  // Advance clock by another 7000ms (to reach end)
  clock.advance(7000);
  player.update_to_now();

  assert(player.position_ms() == 10000);
  assert(player.state() == Player::PlaybackState::Paused);

  // Test 3: Playlist navigation without wrap-around
  Media::MediaMetadata media2("Another Video", 5000);  // 5 seconds
  playlist.add(media2);

  assert(playlist.size() == 2);
  assert(playlist.get(0) != nullptr);
  assert(playlist.get(1) != nullptr);
  assert(playlist.get(2) == nullptr);

  assert(playlist.select(1) == true);
  assert(playlist.current_index() == 1);
  assert(playlist.current() != nullptr);
  assert(playlist.current()->title() == "Another Video");

  assert(playlist.next() == false);  // Already at end
  assert(playlist.prev() == true);
  assert(playlist.current_index() == 0);
  assert(playlist.prev() == false);  // Already at beginning

  // Test 4: Runtime::App smoke test
  Runtime::App app;
  int result = app.run_demo();
  assert(result == 0);

  return 0;
}