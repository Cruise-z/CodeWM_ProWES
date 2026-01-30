from typing import Final
from .baseline import baseline

# 简短描述，可自由修改
desc: Final[str] = "Build tiny Java project (Tank battle game, Maven, Java 11, strict 2-file repo)."

idea: Final[str] = f"""
========================
BASELINE
========================
{baseline}

===========================
PROJECT MODULE: Tank Battle
===========================

Package & Paths

* Package: com.example.tankbattle
* Main class: TankBattle
* File list (and ONLY these two):

  1. pom.xml
  2. src/main/java/com/example/tankbattle/TankBattle.java
* Whitelist is exactly the two paths above; any other path/file is forbidden.

Functional Requirements (Tank Battle)

* World & Camera:

  * Fixed-size 2D arena (e.g., 800×600 logical units) with a simple tile/block grid for obstacles (some solid/indestructible, optional destructible).
  * No scrolling camera required; everything fits the viewport.
* Player Tank:

  * Position (x,y), chassis speed, turret rotation (independent of chassis), and fire cooldown.
  * Controls:

    * Movement: UP/DOWN (W/S) move forward/backward along the chassis facing; LEFT/RIGHT (A/D) rotate the chassis.
    * Turret aim: mouse or Q/E keys rotate turret (document choice); space or mouse click fires a shell if cooldown elapsed.
  * Health/lives: start with fixed HP or lives (choose and document); on zero → player destroyed.
* Enemy Tanks:

  * Spawn a small number initially; optional wave spawns over time.
  * Simple AI: chase/strafe toward player while avoiding solid tiles (greedy/grid-aware steering is sufficient); fire at intervals when roughly aligned/within range.
* Projectiles:

  * Shells travel straight with constant speed; despawn on impact or when off-screen.
  * Collisions with tanks and solid tiles. Hitting a tank deals damage; hitting a destructible block reduces durability; shells do not pass through solid walls.
* Collisions:

  * Use simple AABB or circle approximations.
  * Tanks cannot pass through solid tiles or each other (basic resolution acceptable).
* Scoring & Win/Lose:

  * Gain score for destroying enemy tanks and (optionally) destructible blocks.
  * Win when all enemies (or a final wave) are destroyed; lose when the player is destroyed (inGame=false). Show an overlay text for “You Win” / “Game Over”.
* Rendering (shapes only):

  * Draw arena, blocks, player tank (chassis + turret), enemy tanks, shells, and UI (HP/lives/score/wave).
  * Use primitive shapes (`fillRect`, `fillOval`, `drawLine`, `drawString`); no external assets.
* Timing:

  * Fixed-timestep loop via `javax.swing.Timer` (~16–20 ms). In headless mode, do not create a window; logic must still run.
* Restart:

  * Press R (or documented key) to fully reset state: player HP/lives, score, enemies, cooldowns, positions, and running status.

Keep Typical Single-File Architecture (Tank Battle)

* Maintain a conventional single-source layout with private state and helpers, e.g.:

  * Private fields: arena size; tile grid (with flags: solid/destructible/durability); player state (x,y,angle, turretAngle, hp/lives, cooldown); enemy list (each with x,y,angle,turretAngle,hp,aiCooldown); projectile list (x,y,vx,vy,owner); score; wave counters; `boolean inGame`, `boolean won`; input flags; `java.util.Random rng`; `javax.swing.Timer` loop.
  * Private helpers: `reset()`, `spawnEnemies()/spawnWave()`, `handleInput()`, `moveTank()/integrate()`, `rotateTurret()`, `canMoveTo(x,y)`, `fireShell(owner)`, `stepProjectiles()`, `handleCollisions()`, `damageTank(t, dmg)`, `cleanDeadEntities()`, `checkWinLose()`, and rendering (`paintComponent()/drawScene()`); input handlers via `KeyAdapter` (mouse optional but allowed).
* Without exposing raw internals, add minimal **test hooks** and a nested **self-test suite** as required by the BASELINE. Prefer thin wrappers exposing capabilities (control/step/inspect/determinism) rather than dumping entire structures.

Tank Battle–Specific Test Guidance

* Movement & Rotation:

  * From rest, rotate chassis by a fixed delta on LEFT/RIGHT; forward move updates (x,y) along chassis angle; movement into a solid tile is rejected (position unchanged).
* Turret & Firing:

  * Rotating the turret changes only `turretAngle` (not chassis angle).
  * With cooldown ready, firing spawns exactly one projectile with correct initial position and velocity along `turretAngle`; while cooldown active, firing is ignored.
* Projectile Dynamics:

  * After one tick, a shell advances by `speed * dt`; off-screen shells are removed; on tile impact, shell despawns.
* Damage & Destruction:

  * Projectile hitting an enemy reduces its HP; when HP ≤ 0 the enemy is removed and score increments exactly once; similarly for player damage.
* AI:

  * With deterministic seed and a fixed player position, an enemy advances toward the player and fires when aligned/in range after N ticks (document thresholds).
* Win/Lose:

  * Eliminating all enemies sets `won=true` and stops updates; reducing player HP to zero sets `inGame=false`.
* Restart:

  * After restart, player/enemy/projectile lists reset, grid durability restored, score reset, `inGame=true`, `won=false`, timer ready/running.
* Determinism & Hooks:

  * Provide hooks to set RNG seed; directly set player/enemy positions/angles; spawn a known enemy; fire from player/enemy; and advance one logic tick.
  * Self-tests must call a single-step tick method; avoid sleeps/time-based assertions.

pom.xml Requirements (Tank Battle)

* maven-compiler-plugin: Java 11 (`<source>11</source>`, `<target>11</target>`, `<release>11</release>`); no preview flags.
* exec-maven-plugin: main class is `com.example.tankbattle.TankBattle`.
* Do NOT add JUnit or any other dependencies; only these two files exist.

Output Style (Tank Battle)

* Output exactly two complete files, in this order:

  1. pom.xml (full content)
  2. src/main/java/com/example/tankbattle/TankBattle.java (full content with a top-of-file **Public/Test API Summary** comment that documents the chosen test hooks and how the self-tests use them)
"""
