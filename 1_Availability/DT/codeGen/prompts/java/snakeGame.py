from typing import Final
from .baseline import baseline

# 简短描述，可自由修改
desc: Final[str] = "Build tiny Java project (Snake game, Maven, Java 11, strict 2-file repo)."

idea: Final[str] = f"""
========================
BASELINE
========================
{baseline}

========================
PROJECT MODULE: Snake
========================
Package & Paths
- Package: com.example.snakegame
- Main class: SnakeGame
- File list (and ONLY these two):
  1) pom.xml
  2) src/main/java/com/example/snakegame/SnakeGame.java
- Whitelist is exactly the two paths above; any other path/file is forbidden.

Functional Requirements (Snake)
- Grid: ~30×30 cells; cell size ~10 px.
- Initial state: snake length = 3; initial direction = right; continuous movement on a fixed tick (~100–150 ms).
- Food: randomly placed on empty cells; when the head reaches food, snake grows and a new food spawns immediately.
- Collisions: hitting walls or self ends the run (in-game=false) and stops the scheduler/timer.
- Rendering: draw snake, food, and score using primitive shapes; on game over, draw a simple “Game Over” text.
- Input: arrow keys change direction; immediate reverse is disallowed.

Keep Typical Single-File Architecture (Snake)
- Keep a conventional internal layout with private fields and helpers (e.g., position arrays/lists, length/counters, direction flags, in-game flag, scheduler/timer; private methods like move(), check*(), locate*/spawn*(), and a key listener class).
- Without breaking that architecture, add minimal test hooks and a nested self-test suite as required by the baseline. Prefer thin wrappers to expose the necessary capabilities rather than dumping internal state.

Snake-Specific Test Guidance
- Direction rules: verify legal direction changes and rejection of immediate reverse.
- Eating: deterministically place food (or fix randomness) so that after one tick, growth occurs and counters increment.
- Self-collision: construct a body path so that after advancing ticks, the head overlaps the body → in-game=false and scheduler stops.
- Wall collision: place the head at boundary and advance one tick → in-game=false.
- Restart: after restart, length returns to 3, direction resets to initial, in-game=true, food re-placed; scheduler is ready/running.
- Determinism: expose a seed setter or explicit placement hook so tests are stable; avoid sleeps in self-tests.

pom.xml Requirements (Snake)
- maven-compiler-plugin: Java 11 (<source>, <target>, <release> all 11); no preview.
- exec-maven-plugin: main class is com.example.snakegame.SnakeGame.
- Do NOT add JUnit or any other dependencies; only these two files exist.

Output Style (Snake)
- Output exactly two complete files, in this order:
  1) pom.xml (full content)
  2) src/main/java/com/example/snakegame/SnakeGame.java (full content with a top-of-file Public/Test API Summary comment)
"""
