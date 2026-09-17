"""Core Player: playback state machine, clock-driven position, seeking, volume/mute, playlist-aware navigation.

This module implements the Player class which orchestrates playback of media
items according to the rules defined in the domain. It manages playback state,
position tracking, volume control, and integrates with a ManualClock for
deterministic time progression.
"""

from enum import Enum
from typing import Optional
from .errors import ValidationError, StateError
from .media import Media
from .playlist import Playlist
from .clock import ManualClock


class PlaybackState(Enum):
    """Enumeration of possible playback states for the player.

    The player can be in one of three states:
    - STOPPED: No media is currently playing or paused
    - PLAYING: Media is actively playing
    - PAUSED: Media is paused at its current position
    """
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"

    def __str__(self) -> str:
        """Return string representation of the playback state."""
        return self.value


class Player:
    """Main player class that controls playback of media items.

    This class manages the playback state machine, position tracking,
    volume control, and integrates with a ManualClock for deterministic
    time progression. It coordinates with a Playlist to manage media items.
    """

    def __init__(self, playlist: Playlist, clock: ManualClock) -> None:
        """Initialize the Player with a playlist and clock.

        Args:
            playlist: The playlist containing media items to play
            clock: The clock that drives time progression
        """
        self._playlist = playlist
        self._clock = clock
        self._state = PlaybackState.STOPPED
        self._position = 0.0
        self._volume = 1.0
        self._muted = False
        
        # Subscribe to clock ticks
        self._clock.add_tick_listener(self._on_tick)

    def state(self) -> PlaybackState:
        """Get the current playback state.

        Returns:
            The current PlaybackState (STOPPED, PLAYING, or PAUSED)
        """
        return self._state

    def current_media(self) -> Optional[Media]:
        """Get the currently selected media item.

        Returns:
            The currently selected Media object or None if no media is selected
        """
        return self._playlist.current()

    def position_seconds(self) -> float:
        """Get the current position within the current media in seconds.

        Returns:
            Current position in seconds; 0.0 when no media is selected
        """
        return self._position

    def duration_seconds(self) -> float:
        """Get the duration of the current media in seconds.

        Returns:
            Duration of current media in seconds; 0.0 when no media is selected
        """
        current = self._playlist.current()
        if current is None:
            return 0.0
        return current.duration_seconds

    def play(self) -> None:
        """Start or resume playback of the current media.

        Transitions to PLAYING state if a media item is selected.
        If the playlist is empty, raises StateError.
        If at the end of media (position >= duration), resets to beginning before playing.
        
        Raises:
            StateError: If the playlist is empty
        """
        if self._playlist.is_empty():
            raise StateError("Cannot play: playlist is empty")
            
        current = self._playlist.current()
        if current is None:
            raise StateError("Cannot play: no media selected")
            
        # Reset position if we're at the end
        if self._position >= current.duration_seconds:
            self._reset_position()
            
        self._state = PlaybackState.PLAYING

    def pause(self) -> None:
        """Pause playback of the current media.

        Transitions to PAUSED state if currently PLAYING.
        No-op if already PAUSED or STOPPED.
        """
        if self._state == PlaybackState.PLAYING:
            self._state = PlaybackState.PAUSED

    def stop(self) -> None:
        """Stop playback and reset position to the beginning.

        Transitions to STOPPED state and resets position to 0.0.
        """
        self._state = PlaybackState.STOPPED
        self._reset_position()

    def seek(self, seconds: float) -> float:
        """Seek to a specific position within the current media.

        Args:
            seconds: Target position in seconds
            
        Returns:
            The effective position after seeking (clamped to valid range)
            
        Raises:
            ValidationError: If seconds is NaN or negative infinity
        """
        # Handle special float values
        if seconds != seconds:  # NaN check
            raise ValidationError("Seek position cannot be NaN")
        if seconds == float('-inf'):
            raise ValidationError("Seek position cannot be negative infinity")
            
        current = self._playlist.current()
        if current is None:
            # No media selected, just return 0.0 and remain stopped
            return 0.0
            
        # Clamp to valid range [0, duration]
        duration = current.duration_seconds
        effective_position = max(0.0, min(seconds, duration))
        
        self._position = effective_position
        return effective_position

    def set_volume(self, v: float) -> float:
        """Set the volume level.

        Args:
            v: Volume level (0.0 to 1.0)
            
        Returns:
            The effective volume after clamping (between 0.0 and 1.0)
        """
        # Clamp volume to [0.0, 1.0]
        clamped_volume = max(0.0, min(v, 1.0))
        self._volume = clamped_volume
        return clamped_volume

    def get_volume(self) -> float:
        """Get the current volume level.

        Returns:
            Current volume level (0.0 to 1.0), independent of mute state
        """
        return self._volume

    def mute(self) -> None:
        """Mute the player."""
        self._muted = True

    def unmute(self) -> None:
        """Unmute the player."""
        self._muted = False

    def toggle_mute(self) -> bool:
        """Toggle mute state.

        Returns:
            New mute state (True if muted, False if unmuted)
        """
        self._muted = not self._muted
        return self._muted

    def effective_volume(self) -> float:
        """Get the effective volume considering mute state.

        Returns:
            0.0 if muted, otherwise returns current volume level
        """
        if self._muted:
            return 0.0
        return self._volume

    def next_media(self) -> Optional[Media]:
        """Advance to the next media item in the playlist.

        Returns:
            The next Media object if available, otherwise None
        """
        next_item = self._playlist.next()
        if next_item is not None:
            # Reset position and stop playback
            self._reset_position()
            self._state = PlaybackState.STOPPED
        return next_item

    def previous_media(self) -> Optional[Media]:
        """Go back to the previous media item in the playlist.

        Returns:
            The previous Media object if available, otherwise None
        """
        prev_item = self._playlist.previous()
        if prev_item is not None:
            # Reset position and stop playback
            self._reset_position()
            self._state = PlaybackState.STOPPED
        return prev_item

    def select_index(self, i: int) -> Media:
        """Select a media item by index and reset playback.

        Args:
            i: Zero-based index of the media to select
            
        Returns:
            The selected Media object
        """
        selected = self._playlist.select(i)
        # Reset position and stop playback
        self._reset_position()
        self._state = PlaybackState.STOPPED
        return selected

    def _on_tick(self, delta: float) -> None:
        """Handle clock ticks for advancing playback position.

        This internal method is called by the clock on each tick and
        advances the playback position when in PLAYING state.

        Args:
            delta: Time elapsed since last tick in seconds
        """
        # Only advance position when playing and there's a current media
        if self._state == PlaybackState.PLAYING and self._playlist.current() is not None:
            # Calculate new position
            new_position = self._position + delta
            
            # Get current media duration
            duration = self._playlist.current().duration_seconds
            
            # Check if we've reached the end
            if new_position >= duration:
                # Clamp position to duration and stop
                self._position = duration
                self._state = PlaybackState.STOPPED
            else:
                # Update position normally
                self._position = new_position

    def _reset_position(self) -> None:
        """Reset the playback position to the beginning."""
        self._position = 0.0