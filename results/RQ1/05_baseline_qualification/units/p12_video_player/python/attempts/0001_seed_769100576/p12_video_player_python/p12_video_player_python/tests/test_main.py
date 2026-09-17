"""Protocol-level smoke and core rule tests for the video player.

This module contains deterministic, headless tests that verify the core
functionality of the video player without external dependencies.
Tests drive time deterministically via ManualClock.tick() calls.
"""

import pytest
from video_player import (
    Media, Playlist, ManualClock, Player, PlaybackState,
    ValidationError, StateError, NotFoundError
)


def test_clock_driven_playback_progression():
    """Test clock-driven playback progression: play(), tick advances position; pause() prevents advancement; stopping at end-of-media clamps and transitions to STOPPED."""
    # Setup
    media = Media(id="test", title="Test Media", duration_seconds=10.0)
    playlist = Playlist([media])
    clock = ManualClock()
    player = Player(playlist, clock)
    
    # Initially stopped
    assert player.state() == PlaybackState.STOPPED
    assert player.position_seconds() == 0.0
    
    # Play and advance
    player.play()
    assert player.state() == PlaybackState.PLAYING
    clock.tick(1.0)
    assert player.position_seconds() == 1.0
    
    # Pause should prevent advancement
    player.pause()
    assert player.state() == PlaybackState.PAUSED
    clock.tick(2.0)
    assert player.position_seconds() == 1.0  # Should not advance
    
    # Resume and advance
    player.play()
    assert player.state() == PlaybackState.PLAYING
    clock.tick(3.0)
    assert player.position_seconds() == 4.0
    
    # Advance past end - should clamp and stop
    clock.tick(10.0)
    assert player.position_seconds() == 10.0  # Clamped at duration
    assert player.state() == PlaybackState.STOPPED


def test_seek_clamping():
    """Test seek clamping within [0, duration]."""
    # Setup
    media = Media(id="test", title="Test Media", duration_seconds=10.0)
    playlist = Playlist([media])
    clock = ManualClock()
    player = Player(playlist, clock)
    
    # Seek within range
    pos = player.seek(5.0)
    assert pos == 5.0
    assert player.position_seconds() == 5.0
    
    # Seek below range
    pos = player.seek(-1.0)
    assert pos == 0.0
    assert player.position_seconds() == 0.0
    
    # Seek above range
    pos = player.seek(15.0)
    assert pos == 10.0
    assert player.position_seconds() == 10.0
    
    # Seek with NaN (should raise ValidationError)
    with pytest.raises(ValidationError):
        player.seek(float('nan'))
    
    # Seek with negative infinity (should raise ValidationError)
    with pytest.raises(ValidationError):
        player.seek(float('-inf'))


def test_volume_mute_behavior():
    """Test volume/mute: set_volume clamps to [0,1]; effective_volume reflects mute state; toggle_mute returns new mute status."""
    # Setup
    media = Media(id="test", title="Test Media", duration_seconds=10.0)
    playlist = Playlist([media])
    clock = ManualClock()
    player = Player(playlist, clock)
    
    # Set volume within range
    vol = player.set_volume(0.5)
    assert vol == 0.5
    assert player.get_volume() == 0.5
    assert player.effective_volume() == 0.5
    
    # Set volume below range (should clamp)
    vol = player.set_volume(-0.5)
    assert vol == 0.0
    assert player.effective_volume() == 0.0
    
    # Set volume above range (should clamp)
    vol = player.set_volume(1.5)
    assert vol == 1.0
    assert player.effective_volume() == 1.0
    
    # Mute
    player.mute()
    assert player.effective_volume() == 0.0
    
    # Unmute
    player.unmute()
    assert player.effective_volume() == 1.0
    
    # Toggle mute
    muted = player.toggle_mute()
    assert muted is True
    assert player.effective_volume() == 0.0
    
    muted = player.toggle_mute()
    assert muted is False
    assert player.effective_volume() == 1.0


def test_playlist_navigation_bounds():
    """Test playlist navigation: next/previous bounds; select_index resets position and keeps deterministic state."""
    # Setup
    media1 = Media(id="vid1", title="Video 1", duration_seconds=10.0)
    media2 = Media(id="vid2", title="Video 2", duration_seconds=20.0)
    media3 = Media(id="vid3", title="Video 3", duration_seconds=5.0)
    playlist = Playlist([media1, media2, media3])
    clock = ManualClock()
    player = Player(playlist, clock)
    
    # Start at first item
    assert player.current_media() == media1
    assert player.position_seconds() == 0.0
    assert player.state() == PlaybackState.STOPPED
    
    # Try to go previous from first - should return None and not change state
    prev = player.previous_media()
    assert prev is None
    assert player.state() == PlaybackState.STOPPED
    assert player.position_seconds() == 0.0
    
    # Go to next - should advance to second
    next_media = player.next_media()
    assert next_media == media2
    assert player.state() == PlaybackState.STOPPED
    assert player.position_seconds() == 0.0
    assert player.current_media() == media2
    
    # Go to next from second - should advance to third
    next_media = player.next_media()
    assert next_media == media3
    assert player.state() == PlaybackState.STOPPED
    assert player.position_seconds() == 0.0
    assert player.current_media() == media3
    
    # Try to go next from last - should return None and not change state
    next_media = player.next_media()
    assert next_media is None
    assert player.state() == PlaybackState.STOPPED
    assert player.position_seconds() == 0.0
    assert player.current_media() == media3
    
    # Go back to second
    prev_media = player.previous_media()
    assert prev_media == media2
    assert player.state() == PlaybackState.STOPPED
    assert player.position_seconds() == 0.0
    assert player.current_media() == media2
    
    # Select index 0 (first) - should reset position and state
    selected = player.select_index(0)
    assert selected == media1
    assert player.state() == PlaybackState.STOPPED
    assert player.position_seconds() == 0.0
    assert player.current_media() == media1
    
    # Select index 2 (third) - should reset position and state
    selected = player.select_index(2)
    assert selected == media3
    assert player.state() == PlaybackState.STOPPED
    assert player.position_seconds() == 0.0
    assert player.current_media() == media3
    
    # Select invalid index - should raise NotFoundError
    with pytest.raises(NotFoundError):
        player.select_index(5)
    
    # Empty playlist tests
    empty_playlist = Playlist([])
    empty_player = Player(empty_playlist, clock)
    
    assert empty_player.current_media() is None
    assert empty_player.state() == PlaybackState.STOPPED
    assert empty_player.position_seconds() == 0.0
    assert empty_player.duration_seconds() == 0.0
    
    # Attempt to play empty playlist should raise StateError
    with pytest.raises(StateError):
        empty_player.play()
    
    # Attempt to select index on empty playlist should raise NotFoundError
    with pytest.raises(NotFoundError):
        empty_player.select_index(0)
    
    # Attempt to navigate on empty playlist should return None
    assert empty_player.next_media() is None
    assert empty_player.previous_media() is None