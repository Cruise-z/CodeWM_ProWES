from typing import Final
from .baseline import baseline

# 简短描述，可自由修改
desc: Final[str] = "Build tiny Java project (Game 2048, Maven, Java 11, strict 2-file repo)."

idea: Final[str] = f"""
========================
BASELINE
========================
{baseline}

========================
PROJECT MODULE: Game 2048
========================

Package & Paths

* Package: com.example.game2048
* Main class: Game2048
* File list (and ONLY these two):

  1. pom.xml
  2. src/main/java/com/example/game2048/Game2048.java
* Whitelist is exactly the two paths above; any other path/file is forbidden.

Functional Requirements (2048)

* Grid: fixed 4×4 board of integer tiles (0 means empty; non-zero tiles are powers of two).
* Initial state: start with two tiles randomly placed (2 or 4); score = 0; game is running.
* Moves: Arrow keys (UP, DOWN, LEFT, RIGHT) shift tiles:

  * Slide tiles toward the move direction, compressing gaps.
  * Merge equal adjacent tiles once per move (per line) according to the move direction order.
  * A tile can contribute to at most one merge per move.
  * Score increases by the value of each created (merged) tile.
* Spawning: After a **successful** move (board changes), spawn exactly one new tile (value 2 with high probability, e.g., 90%; value 4 with low probability, e.g., 10%) at a random empty cell.
* Win/Lose:

  * Win when any tile reaches 2048 (set a “won” state but keep allowing moves, or freeze—choose and document behavior).
  * Game over when no legal moves remain in any direction (no empty cells and no adjacent equal tiles).
* Rendering: draw the 4×4 grid, each tile’s value, and the score using primitive shapes/text only (no external assets). Show a simple “You Win” or “Game Over” overlay when relevant.
* Input: arrow keys perform moves; Esc or R may trigger restart (optional but recommended).

Keep Typical Single-File Architecture (2048)

* Use a conventional single-file layout with private state and helpers, for example:

  * Private fields: `int[][] board`, `int score`, `boolean inGame`, `boolean won`, `java.util.Random rng`, optional scheduler/timer for repaint.
  * Private helpers: `compress/merge/move` per direction, `spawnRandomTile()`, `canMove()`, `reset()`, and rendering routines (`paintComponent()` / `drawBoard()`).
  * An input handler (e.g., KeyAdapter) to map arrow keys to moves.
* Without breaking that architecture, add minimal **test hooks** and a nested **self-test suite** as required by the BASELINE. Prefer thin wrappers that expose capabilities (control/step/inspect/determinism) rather than exposing raw internal fields.

2048-Specific Test Guidance

* Move mechanics:

  * Verify tile sliding removes gaps correctly in each direction.
  * Verify merging rules: each tile merges at most once per move; merging follows the correct directional order; no double-merge cascades in a single move.
* Scoring: verify score increases exactly by the sum of newly created (merged) tiles in a move.
* Spawning:

  * Verify a new tile spawns **only** when the board changed; verify spawn value distribution is controllable/deterministic in tests.
  * Provide a deterministic hook: seed setter and/or a method to spawn a tile at a specified cell with a specified value (test-only).
* Win/Lose:

  * Win: force-create a 2048 tile and assert “won” state is set (and document whether further moves are allowed).
  * Game over: construct a no-move board and assert `inGame=false` after checking moves.
* Restart: after restart, board contains exactly two tiles (2/4), score = 0, `inGame=true`, `won=false`, RNG ready.
* Determinism: expose seed injection and/or direct board setters for self-tests; avoid sleeps/time-based logic in self-tests.

pom.xml Requirements (2048)

* maven-compiler-plugin: Java 11 (`<source>11</source>`, `<target>11</target>`, `<release>11</release>`); no preview flags.
* exec-maven-plugin: main class is `com.example.game2048.Game2048`.
* Do NOT add JUnit or any other dependencies; only these two files exist.

Output Style (2048)

* Output exactly two complete files, in this order:
  1. pom.xml (full content)
  2. src/main/java/com/example/game2048/Game2048.java (full content with a top-of-file **Public/Test API Summary** comment that documents the chosen test hooks and how the self-tests use them)
"""
