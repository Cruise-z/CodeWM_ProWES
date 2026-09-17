#ifndef INCLUDE_RUNTIME_APP_H_
#define INCLUDE_RUNTIME_APP_H_

namespace Runtime {

/// Headless runtime wiring for a small deterministic demo.
class App {
 public:
  /// Constructs an application instance.
  App() = default;

  /// Runs a small deterministic demo of the video player components.
  ///
  /// This method assembles a ManualClock, Playlist, MediaMetadata,
  /// and Player, then demonstrates basic playback functionality
  /// without any I/O loops or interactive elements.
  ///
  /// @return 0 on successful completion.
  int run_demo();
};

}  // namespace Runtime

#endif  // INCLUDE_RUNTIME_APP_H_