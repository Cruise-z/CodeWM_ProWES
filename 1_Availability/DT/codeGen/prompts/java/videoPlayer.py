from typing import Final
from .baseline import baseline

# 简短描述，可自由修改
desc: Final[str] = "Build tiny Java project (Video player App, Maven, Java 11, strict 2-file repo)."

idea: Final[str] = f"""
========================
BASELINE
========================
{baseline}

===========================================================
PROJECT MODULE: Video Player App (No Third-Party Libraries)
===========================================================

Package & Paths

* Package: com.example.videoplayer
* Main class: VideoPlayerApp
* File list (and ONLY these two):

  1. pom.xml
  2. src/main/java/com/example/videoplayer/VideoPlayerApp.java
* Whitelist is exactly the two paths above; any other path/file is forbidden.

Functional Requirements (Video Player, No Third-Party Libs)

* **Library Constraint (MANDATORY): Do not use any third-party libraries.**

  * Use only **standard Java SE APIs** and/or **JavaFX**.
  * **Disallowed:** vlcj, JMF, FFmpeg bindings, or any external media/utility libs.
  * Treat “video” as a **sequence of still images**; no real video decoding.
* Sources:

  1. **Directory of images** (PNG/JPEG) sorted naturally/lexicographically (e.g., `frame_0001.png`, `2.jpg`).
  2. **In-memory frames** for tests (Swing: `BufferedImage`; JavaFX: `javafx.scene.image.Image`).
  3. (Optional) Animated GIF using JDK/JavaFX built-ins if trivial; otherwise document unsupported.
* Playback & Controls:

  * Play / Pause / Stop.
  * Step to next/previous frame.
  * Seek by **frame index** (clamped to [0, total-1]).
  * Playback speed: set **FPS** and **rate multiplier** (0.5× / 1× / 2×).
  * Loop toggle (default off; document behavior).
* Timing:

  * If **Swing/AWT**: use `javax.swing.Timer`.
  * If **JavaFX**: use `Timeline` or `AnimationTimer` with your own accumulator.
  * Provide a **single-step `tick()`** method used by both runtime and self-tests (no sleeps).
* Rendering:

  * Swing: draw current `BufferedImage` on a `JPanel` (`paintComponent`/`Graphics2D`), overlay HUD text.
  * JavaFX: draw to a `Canvas` or `ImageView`, overlay HUD text.
  * No external assets/themes.
* File I/O:

  * Load frames from a directory (extensions: `.png`, `.jpg`, `.jpeg`, `.gif` if supported).
  * Optional: save current frame to PNG using standard APIs (Swing: `ImageIO`; JavaFX: documented approach).
* Headless behavior:

  * If headless, **do not** create a window; logic and self-tests must still run.

Keep Typical Single-File Architecture (Video Player)

* Single source file with private state and helpers, e.g.:

  * Private fields: list of frames, `int current`, `double fps`, `double rate`, `boolean playing`, `boolean loop`, the scheduler (`Timer`/`Timeline`/`AnimationTimer`), optional source directory and sorter.
  * Private helpers: `loadFromDirectory(Path)`, optional `loadFromGif(Path)`, `setFrames(...)`, `render(...)`, `restart()`, `seek(int)`, `step(int delta)`, `applyRate(double)`, and **`tick()`**.
  * Input handlers: Space (play/pause), Left/Right (prev/next), Up/Down (rate), Home/End (first/last), R (restart), L (loop).
* Without exposing raw internals, add minimal **test hooks** and a nested **self-test suite** per the BASELINE. Prefer thin wrappers exposing capabilities (load/control/tick/inspect/determinism).

Video Player–Specific Test Guidance

* Loading & ordering:

  * Given synthetic filenames, verify natural/lexicographic sort and correct `totalFrames`.
  * In-memory injection: set distinct color frames; assert counts and indices.
* Playback tick:

  * With `fps=10`, `rate=1.0`, N deterministic `tick()` calls advance exactly N frames modulo loop; paused → no advancement.
  * Changing `rate` to 2.0 doubles progression; to 0.5 halves it. Document accumulator/rounding policy.
* Seek & clamp:

  * Seeking outside bounds clamps to valid range.
* Looping:

  * Loop on: advancing past last wraps to 0; loop off: stay at last.
* Restart:

  * `restart()` sets index=0, `playing=false`, preserves frames/fps/rate defaults.
* Determinism:

  * Tests drive logic via `tick()`; no sleeps or wall-clock dependencies. Use in-memory frames for assertions.
* Optional GIF:

  * If implemented, ensure expected frame count and basic pixel validation; else mark unsupported and skip.

pom.xml Requirements (Video Player)

* **No third-party libraries.**

  * If using **Swing/AWT only**: keep dependencies minimal (just `maven-compiler-plugin` + `exec-maven-plugin`).
  * If using **JavaFX**: include **only** OpenJFX modules (`javafx-base`, `javafx-graphics`, `javafx-controls`) and **no other libraries**. Provide `javafx.version` and optional `javafx.platform` classifier property (e.g., pass `-Djavafx.platform=linux`).
* maven-compiler-plugin: Java 11 (`<source>11</source>`, `<target>11</target>`, `<release>11</release>`); no preview flags.
* exec-maven-plugin: main class is `com.example.videoplayer.VideoPlayerApp`.

Output Style (Video Player)

* Output exactly two complete files, in this order:

  1. pom.xml (full content; if JavaFX chosen, include only OpenJFX; otherwise Swing/AWT with no extra deps)
  2. src/main/java/com/example/videoplayer/VideoPlayerApp.java (full content with a top-of-file **Public/Test API Summary** comment documenting the chosen test hooks and how self-tests drive load/control/seek/tick/loop logic without any third-party libraries)
"""
