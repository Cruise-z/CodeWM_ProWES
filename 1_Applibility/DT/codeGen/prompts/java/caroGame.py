from typing import Final
from .baseline import baseline

# 简短描述，可自由修改
desc: Final[str] = "Build tiny Java project (Caro game, Maven, Java 11, strict 2-file repo)."

idea: Final[str] = f"""
========================
BASELINE
========================
{baseline}

===========================================
PROJECT MODULE: Caro (Gomoku/Five-in-a-Row)
===========================================

Package & Paths

* Package: com.example.caro
* Main class: CaroGame
* File list (and ONLY these two):

  1. pom.xml
  2. src/main/java/com/example/caro/CaroGame.java
* Whitelist is exactly the two paths above; any other path/file is forbidden.

Functional Requirements (Caro)

* Board:

  * Fixed square grid (e.g., 15×15). Cell value: 0 = empty, 1 = X, 2 = O.
  * Cell size for rendering ~24–32 px (choose and document a constant).
* Turns:

  * Two human players alternate (X goes first). A move selects an empty cell and places the current player’s mark.
  * Illegal moves (occupied/out-of-bounds) are rejected and do not change turn.
* Win Condition:

  * **Exactly five** contiguous marks in a straight line (horizontal, vertical, or either diagonal) **wins** the game. Overlines (6+ in a row) **do not** count as a win.
* Draw:

  * If the board is full and no one has exactly five, the game is a draw and ends.
* Rendering (shapes only):

  * Draw grid lines, X/O marks (simple lines/circles), and the current player/score text.
  * On win/draw, overlay a simple “X Wins”, “O Wins”, or “Draw” message.
* Input:

  * Mouse click: place a mark in the clicked cell (if legal).
  * Keyboard (recommended): arrow keys move a highlight cursor; Enter to place; R to restart.
* Timing:

  * No real-time physics needed. If a `javax.swing.Timer` is used, it’s only for repaint/UX. In headless mode, do not create a window.

Keep Typical Single-File Architecture (Caro)

* Single source file with private state and helpers, e.g.:

  * Private fields: `int size`, `int[][] board`, `boolean inGame`, `int currentPlayer` (1 or 2), `int movesMade`, optional cursor row/col for keyboard, optional `javax.swing.Timer` for periodic repaint.
  * Private helpers: `reset()`, `isLegalMove(r,c)`, `applyMove(r,c)`, `checkWinFrom(r,c)`, `hasAnyWin()`, `isBoardFull()`, `evaluateLineCount(...)`, rendering methods `paintComponent()/drawGrid()/drawMarks()/drawOverlay()`, and input handlers (KeyAdapter/MouseAdapter).
* Without exposing raw internals, add minimal **test hooks** and a nested **self-test suite** as required by the BASELINE. Prefer thin wrappers exposing capabilities (control/place/inspect/restart/determinism) rather than dumping the entire board.

Caro-Specific Test Guidance

* Legal/Illegal Moves:

  * Placing on an empty cell succeeds and flips `currentPlayer`.
  * Placing on an occupied cell or out-of-bounds fails and does not change `currentPlayer`.
* Win Detection (exactly five):

  * Construct lines of exactly five horizontally, vertically, and both diagonals → win triggers; game ends (`inGame=false`).
  * Construct a line of six in a row → **no win** (overline rule), continue playing.
* Draw:

  * Fill a synthetic board with no five-in-a-row → assert draw and `inGame=false`.
* Turn Order:

  * Verify X starts; after a legal move, it becomes O; illegal attempts don’t flip the turn.
* Restart:

  * After restart, board is cleared to zeros, `inGame=true`, `currentPlayer=X`, `movesMade=0`.
* Determinism & Hooks:

  * Provide test hooks to place marks programmatically (bypassing mouse) with legality checks.
  * Provide an inspection hook to read the **resulting state for assertions** (e.g., current player, inGame flag, winner enum/flag, last move, and read-only board snapshot or a query method like `getCell(r,c)`).
  * Self-tests should call a single “step/applyMove” capability rather than using sleeps; do not rely on timing.

pom.xml Requirements (Caro)

* maven-compiler-plugin: Java 11 (`<source>11</source>`, `<target>11</target>`, `<release>11</release>`); no preview flags.
* exec-maven-plugin: main class is `com.example.caro.CaroGame`.
* Do NOT add JUnit or any other dependencies; only these two files exist.

Output Style (Caro)

* Output exactly two complete files, in this order:

  1. pom.xml (full content)
  2. src/main/java/com/example/caro/CaroGame.java (full content with a top-of-file **Public/Test API Summary** comment that documents the chosen test hooks and how the self-tests use them)
"""
