from typing import Final
from .baseline import baseline

# 简短描述，可自由修改
desc: Final[str] = "Build tiny Java project (Brick breaker game, Maven, Java 11, strict 2-file repo)."

idea: Final[str] = f"""
========================
BASELINE
========================
{baseline}

==============================================
PROJECT MODULE: Brick Breaker (Arkanoid-style)
==============================================

Package & Paths

* Package: com.example.brickbreaker
* Main class: BrickBreaker
* File list (and ONLY these two):

  1. pom.xml
  2. src/main/java/com/example/brickbreaker/BrickBreaker.java
* Whitelist is exactly the two paths above; any other path/file is forbidden.

Functional Requirements (Brick Breaker)

* World:

  * Rectangular playfield; top/left/right are solid walls; bottom is a death zone.
  * One controllable paddle at the bottom; one ball that bounces off walls, paddle, and bricks.
* Paddle:

  * Moves horizontally via keyboard (LEFT/RIGHT or A/D). Clamp to playfield; fixed speed per tick.
  * Optional mouse support is allowed but keyboard must exist.
* Ball:

  * Circular (or small square) with position and velocity; constant speed magnitude (or bounded min/max).
  * Launch mechanic: ball starts “stuck” to paddle; pressing SPACE launches with an initial upward velocity.
* Bricks:

  * Grid of bricks (e.g., 8–12 columns × 4–8 rows). Each brick has durability (at least 1). When durability hits 0, it disappears and increments score.
  * Empty gaps allowed; durable bricks (2+) require multiple hits (optional but recommended).
* Collisions:

  * Ball-wall: reflect on left/right/top; hitting bottom costs a life.
  * Ball-paddle: reflect upward; reflection angle depends on the relative hit position along the paddle (more angle near edges). **Document the exact mapping**: use `h = clamp((hitX - paddleCenterX) / (paddleWidth/2), -1, 1)`; let `θ = h * θ_max` (default `θ_max = 60°`). After paddle hit, set velocity to constant speed `S` with `vx = S * cos(θ)`, `vy = -|S * sin(θ)|`.
  * Ball-brick: reflect away from collision side, reduce brick durability, remove at 0, increment score exactly once per destroyed brick.
  * Use simple AABB or circle-vs-AABB approximations; prevent tunneling with small time steps or sequential axis resolution.
* Lives & Win/Lose:

  * Start with a fixed number of lives (e.g., 3). Missing the ball (ball crosses bottom) decrements lives and resets ball “stuck” on the paddle; if lives reach 0 → game over (`inGame=false`).
  * Win when all bricks are destroyed (no bricks remain). Show a “You Win” overlay; stop the scheduler/timer or freeze updates.
* Rendering (shapes only):

  * Draw paddle, ball, bricks (color/outline by durability), score, lives. On game over or win, show a simple overlay text.
* Timing:

  * Use a fixed loop tick via `javax.swing.Timer` (~16–20 ms). In headless mode, do not create a window but logic must still be runnable.
* Restart:

  * Press R (or documented key) to fully reset state: lives, score, brick layout, paddle/ball positions, and running status.

Keep Typical Single-File Architecture (Brick Breaker)

* Maintain a conventional single-source layout with private state and helpers, e.g.:

  * Private fields: playfield width/height, paddle x/width/speed, ball position (x,y), velocity (vx,vy), radius, constant speed, list/array of bricks (with x,y,w,h,durability,alive), score, lives, `boolean inGame`, `boolean won`, `boolean ballStuckToPaddle`, input flags, `java.util.Random rng`, and a `javax.swing.Timer` for the loop.
  * Private helpers: `reset()`, `resetBallOnPaddle()`, `stepPhysics()`, `movePaddle()`, `handleCollisionsWalls()`, `handleCollisionPaddle()`, `handleCollisionsBricks()`, `removeDestroyedBricksAndScore()`, `checkWinLose()`, and rendering methods `paintComponent()/drawScene()`. Input handlers via `KeyAdapter` (mouse optional).
* Without exposing raw internals, add minimal **test hooks** and a nested **self-test suite** **inside `BrickBreaker.java`** only (no extra files). Prefer thin wrappers exposing capabilities (control/step/inspect/determinism) instead of dumping entire internal structures. The self-test suite must run in headless environments and never create a window while testing.

Brick Breaker–Specific Test Guidance

* Wall bounce:

  * Place ball near left/right/top walls with velocity toward the wall; after one tick, assert reflection (sign of component flips) and conserved speed magnitude within tolerance.
* Paddle bounce:

  * Position ball just above the paddle moving downward; after one tick, assert vertical reflection and angle modulation per the documented formula: hits near paddle edges produce larger |vx| than center hits, and vy is upward.
* Brick collision & scoring:

  * Aim ball at a brick; after collision, durability decrements by 1, brick remains if >0, or is removed if 0; score increments **exactly once** when a brick is destroyed; velocity reflects away from impact side.
  * For multi-hit bricks (durability≥2), verify multiple hits required and score only on final destruction.
* Lose life:

  * Move ball below the bottom boundary; assert lives–=1, ball becomes stuck to paddle, and game continues if lives>0; if lives==0, `inGame=false`.
* Win condition:

  * Clear all bricks deterministically; assert `won=true`, `inGame=false` (or paused), and timer stopped/frozen per documented behavior.
* Restart:

  * After pressing R (or calling a restart hook), assert lives reset (e.g., 3), score=0, bricks restored, paddle/ball reset, `inGame=true`, `won=false`, and timer ready/running.
* Determinism & hooks:

  * Provide hooks to set RNG seed and/or programmatically set ball position/velocity, paddle position, and a fixed brick layout. Tests should call a single-step tick to avoid sleeps and flaky timing.

Self-Test Logic Notes (Brick Breaker-specific; must live inside BrickBreaker.java)

**Goal & Scope**

* All self-tests are implemented as a **nested self-test module inside `BrickBreaker.java`**. No external test files or libraries (no JUnit).
* Cover: wall/paddle/brick collisions, scoring, multi-hit bricks, losing lives, win condition, restart, input handling, clamp logic, timer freeze on win/lose, determinism (fixed tick), and tunneling prevention via sequential axis resolution or small `dt`.

**How to Run**

* Launch with `--self-test` to run only the self-tests and exit (no UI/CLI loop).
* Exit code: `0` if all tests pass; `1` if any fail.
* When not in `--self-test`, run normally (create window only if not headless).

**Headless Guarantee**

* Detect headless via `GraphicsEnvironment.isHeadless()`. In self-test mode or when headless, **do not create any Swing windows** or start the real `Timer`. Tests must drive logic via a manual tick.

**Testable Hooks (thin wrappers; no leaking mutable internals)**

* `testReset(long rngSeed, int cols, int rows, int durabilityDefault)` — rebuild bricks deterministically, reset score/lives/state, place paddle/ball at defaults, set RNG seed.
* `testSetBall(double x, double y, double vx, double vy, boolean stuck)` — direct ball state control for setup.
* `testSetPaddle(double x)` — set paddle x (clamped inside playfield).
* `testLoadLayout(int[][] durabilityMatrix)` — replace brick layout with a deterministic matrix (0 = empty).
* `testTickOnce(double dtMillis)` — perform exactly one physics step using the provided fixed `dt` (bypasses Swing `Timer`).
* `testPressKeys(boolean left, boolean right, boolean space, boolean launchIfStuck)` — simulate a single-frame input sample; if `launchIfStuck` and SPACE is true, ball detaches with initial upward velocity.
* `testSnapshot()` — returns an immutable DTO snapshot containing: positions/velocities, `score`, `lives`, `inGame`, `won`, `ballStuckToPaddle`, remaining bricks count, and (optionally) a compact list of bricks’ `(col,row,durability)` still alive. Never return internal arrays or mutable references.

**Determinism Requirements**

* Use a constant speed `S` for the ball; after any collision, normalize `(vx,vy)` to magnitude `S` (within small epsilon).
* Default tick `dt` is fixed (e.g., `16ms`), and `testTickOnce(dt)` uses the provided value exactly.
* Reflection formula off paddle is fixed and documented (see Functional Requirements).
* Brick layout created by `testReset` or `testLoadLayout` must be repeatable given the same inputs.
* All coordinates/time-based checks must be independent of system time or frame pacing.

**Assertions & Cases**

* `[WallBounce.Left/Right/Top]` After one `testTickOnce`, the component of velocity along the normal flips sign; `speed≈S` within tolerance (e.g., `1e-6` relative).
* `[PaddleBounce.Center/Edge]` Place ball just above paddle with downward `vy`; after tick, `vy<0` and `|vx_edge| > |vx_center|` consistent with `θ = h * θ_max`.
* `[Brick.HitOnce]` One-hit brick decremented to `0` → removed; score += 1; velocity reflects away from the collision side.
* `[Brick.MultiHit]` Durability `2+`: requires multiple ticks/hits; score increments **only** when durability reaches `0`.
* `[Life.Lose]` Move ball beyond bottom (`y > bottom`) and tick: `lives--`; ball becomes stuck on paddle; if `lives==0` then `inGame=false`.
* `[Win.AllCleared]` Destroy all bricks deterministically: `won=true`, `inGame=false` (or paused); timer is not advancing game state (in self-test we check that `testTickOnce` does nothing further once won).
* `[Restart]` Call restart hook or simulate `R`: lives restored (e.g., 3), score reset to 0, layout restored, flags `inGame=true`, `won=false`, ball stuck to paddle at spawn.
* `[Clamp.Paddle]` Large left/right input cannot move paddle out of bounds after repeated ticks.
* `[Searchless/No-UI]` In `--self-test`, no window is created and the Swing `Timer` is not started.
* `[NoTunneling.SequentialAxis]` Fast ball toward a thin brick still registers collision when advancing X then Y (or with smaller `dt`) per your chosen method; include a targeted case.

**Self-Test Output Protocol (machine-friendly)**

* Per test line: `[OK] <CaseName>` or `[FAIL] <CaseName>: <reason>`.
* Final two lines (exact):

  * `TOTAL=<N> PASSED=<P> FAILED=<F>`
  * `SELF-TEST PASS` **or** `SELF-TEST FAIL`

**Failure Policy**

* Throw `IllegalArgumentException` for invalid paddle-ball setup in hooks (e.g., NaN, infinite, negative radii), with clear messages for quick diagnosis.
* Self-tests should catch and report as `[FAIL]` rather than letting exceptions crash the JVM (except on catastrophic setup errors).

**Prohibitions**

* Do not expose internal mutable collections or component references.
* Do not rely on system default timezone or wall-clock delays.
* No threads/concurrency in tests; the game loop’s `Timer` is only used in interactive mode.
* No file or network I/O.

pom.xml Requirements (Brick Breaker)

* maven-compiler-plugin: Java 11 (`<source>11</source>`, `<target>11</target>`, `<release>11</release>`); no preview flags.
* exec-maven-plugin: main class is `com.example.brickbreaker.BrickBreaker`.
* Do NOT add JUnit or any other dependencies; only these two files exist.

Output Style (Brick Breaker)

* Output exactly two complete files, in this order:

  1. pom.xml (full content)
  2. src/main/java/com/example/brickbreaker/BrickBreaker.java (full content with a top-of-file **Public/Test API Summary** comment that documents the chosen test hooks and how the self-tests use them).
     **Explicitly: the entire self-test module is implemented inside `BrickBreaker.java`.**
"""
