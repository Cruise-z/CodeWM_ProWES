from typing import Final
from .baseline import baseline

# 简短描述，可自由修改
desc: Final[str] = "Build tiny Java project (Flappy bird game, Maven, Java 11, strict 2-file repo)."

idea: Final[str] = f"""
========================
BASELINE
========================
{baseline}

===========================
PROJECT MODULE: Flappy Bird
===========================

Package & Paths

* Package: com.example.flappy
* Main class: FlappyBird
* File list (and ONLY these two):

  1. pom.xml
  2. src/main/java/com/example/flappy/FlappyBird.java
* Whitelist is exactly the two paths above; any other path/file is forbidden.

Functional Requirements (Flappy Bird)

* World & Physics:

  * Single bird with vertical motion under gravity; integrate velocity and position per tick.
  * A flap (Space / UP arrow / mouse click) applies an instantaneous upward impulse to the bird’s vertical velocity.
  * Clamp vertical velocity to a reasonable terminal range to avoid numeric blow-ups.
* Pipes:

  * Generate vertical pipe pairs (top + bottom) with a constant horizontal speed moving left.
  * Each pair has a vertical gap of fixed or configurable size; the gap’s center is randomized within bounds.
  * Pipes spawn at fixed time or distance intervals; when off-screen they are removed.
* Scoring:

  * When the bird successfully passes a pipe pair (bird’s x crosses the pipe pair’s x midpoint without collision), increment score by 1 exactly once for that pair.
* Collisions:

  * End the run (`inGame=false`) and stop the scheduler/timer on any collision between the bird and a pipe rectangle or when hitting top/bottom world bounds (ceiling/floor).
  * Rectangle-vs-rectangle (or circle-vs-rect approximated by a bounding box) collision detection is acceptable.
* Rendering (shapes only):

  * Draw background, the bird (circle/oval), pipes (rectangles), ground/ceiling guides if desired, and the current score as text.
  * On game over, overlay a simple “Game Over” message and show a restart hint.
* Input:

  * Space / UP arrow / mouse click triggers flap.
  * Pressing R (or another documented key) restarts the game.
* Timing:

  * Use a fixed loop tick via `javax.swing.Timer` (~16–30 ms). In headless mode, logic must still be runnable without creating a window.

Keep Typical Single-File Architecture (Flappy Bird)

* Maintain a conventional single-source layout with private state and helpers, e.g.:

  * Private fields: bird vertical position/velocity, gravity constant, flap impulse, terminal velocity, list/queue of pipes (each pipe stores x-position and gap center), pipe speed, gap size, spawn interval accumulator, score, `boolean inGame`, `java.util.Random rng`, and an optional `javax.swing.Timer` for the game loop.
  * Private helpers: `reset()`, `spawnPipe()`, `stepPhysics()`, `stepPipesAndScoring()`, `checkCollisions()`, `paintComponent()/drawScene()`, and input handlers (KeyAdapter / MouseAdapter).
* Without breaking that architecture, add minimal **test hooks** and a nested **self-test suite** as required by the BASELINE. Prefer thin wrappers exposing capabilities (control/step/inspect/determinism) rather than exposing raw internal fields.

Flappy Bird–Specific Test Guidance

* Physics & Flap:

  * With no flap, after one tick the bird’s velocity increases by gravity and the position updates accordingly.
  * After a flap, velocity receives the upward impulse (reduced numeric value), and subsequent ticks follow gravity, honoring terminal velocity clamps.
* Pipes & Scrolling:

  * After a deterministic number of ticks, a new pipe pair spawns at the expected x; pipes move left by `speed * dt` per tick.
  * Off-screen pipes are pruned; the number of active pipes matches expectations after N ticks.
* Scoring:

  * When the bird passes a pipe pair’s midpoint without collision, score increments exactly once for that pair; repeated ticks do not double-count.
* Collisions:

  * Position the bird to overlap a pipe rectangle and advance one tick → `inGame=false`, scheduler/timer stopped.
  * Force bird to cross ceiling or floor bounds and advance one tick → `inGame=false`.
* Restart:

  * After restart, the bird returns to initial position/velocity, pipes are cleared, score resets to 0, `inGame=true`, and the scheduler/timer is ready/running.
* Determinism:

  * Provide a seed setter and/or hooks to set the next pipe gap Y (and optional spawn schedule) so tests can construct stable pass/collision scenarios.
  * Self-tests should call a single-step tick method rather than relying on real-time sleeps.

pom.xml Requirements (Flappy Bird)

* maven-compiler-plugin: Java 11 (`<source>11</source>`, `<target>11</target>`, `<release>11</release>`); no preview flags.
* exec-maven-plugin: main class is `com.example.flappy.FlappyBird`.
* Do NOT add JUnit or any other dependencies; only these two files exist.

Output Style (Flappy Bird)

* Output exactly two complete files, in this order:

  1. pom.xml (full content)
  2. src/main/java/com/example/flappy/FlappyBird.java (full content with a top-of-file **Public/Test API Summary** comment that documents the chosen test hooks and how the self-tests use them)
"""
