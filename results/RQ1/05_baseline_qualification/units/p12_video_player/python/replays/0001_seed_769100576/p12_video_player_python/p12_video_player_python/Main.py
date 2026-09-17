"""Runtime bootstrap and small demo for the video player application.

This module demonstrates the usage of the video player components by
constructing a playlist, a deterministic ManualClock, and a Player,
performing a few scripted operations, and exiting.
"""

from video_player import Media, Playlist, ManualClock, Player, PlaybackState


def main():
    """Demonstrate the video player functionality with deterministic operations."""
    # Create some media items
    media1 = Media(id="vid1", title="Introduction", duration_seconds=10.0)
    media2 = Media(id="vid2", title="Main Content", duration_seconds=20.0)
    media3 = Media(id="vid3", title="Conclusion", duration_seconds=5.0)

    # Create a playlist
    playlist = Playlist([media1, media2, media3])

    # Create a deterministic clock
    clock = ManualClock()

    # Create a player
    player = Player(playlist, clock)

    # Demo: Play the first media
    print("Starting playback...")
    player.play()
    print(f"State: {player.state()}")
    print(f"Current media: {player.current_media().title if player.current_media() else None}")

    # Advance time - should progress position
    clock.tick(1.0)
    print(f"Position after 1 second: {player.position_seconds()}")

    # Seek to a specific position
    effective_pos = player.seek(5.0)
    print(f"Seeked to 5.0 seconds, effective position: {effective_pos}")

    # Pause playback
    player.pause()
    print(f"State after pause: {player.state()}")

    # Advance time - should not affect position while paused
    clock.tick(2.0)
    print(f"Position after 2 seconds while paused: {player.position_seconds()}")

    # Resume playback
    player.play()
    print(f"State after resume: {player.state()}")

    # Advance time again - should progress position
    clock.tick(3.0)
    print(f"Position after 3 seconds: {player.position_seconds()}")

    # Skip to next media
    next_media = player.next_media()
    print(f"Next media: {next_media.title if next_media else None}")
    print(f"State after next: {player.state()}")
    print(f"Position after next: {player.position_seconds()}")

    # Seek to end of current media
    player.seek(player.duration_seconds())
    print(f"Seeked to end of media, position: {player.position_seconds()}")

    # Advance time - should trigger stop at end
    clock.tick(1.0)
    print(f"Position after advancing past end: {player.position_seconds()}")
    print(f"State after reaching end: {player.state()}")

    # Play again (should reset position and start from beginning)
    player.play()
    print(f"State after playing again: {player.state()}")
    print(f"Position after restart: {player.position_seconds()}")

    # Demonstrate volume control
    player.set_volume(0.5)
    print(f"Volume set to 0.5, effective volume: {player.effective_volume()}")

    # Mute
    player.mute()
    print(f"After muting, effective volume: {player.effective_volume()}")

    # Unmute
    player.unmute()
    print(f"After unmuting, effective volume: {player.effective_volume()}")

    # Toggle mute
    muted = player.toggle_mute()
    print(f"After toggle mute, mute state: {muted}")
    print(f"After toggle mute, effective volume: {player.effective_volume()}")

    # Select different media by index
    selected_media = player.select_index(0)
    print(f"Selected media by index 0: {selected_media.title}")
    print(f"State after selecting index: {player.state()}")
    print(f"Position after selecting index: {player.position_seconds()}")


if __name__ == "__main__":
    main()