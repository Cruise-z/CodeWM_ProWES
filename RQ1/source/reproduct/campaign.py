#!/usr/bin/env python3
"""Resumable 42-unit architecture, seed-search, and evidence campaign."""

from __future__ import annotations

import argparse
import asyncio
import csv
import fcntl
import hashlib
import json
import os
import platform
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


REPRO_ROOT = Path(__file__).resolve().parent
REPO_ROOT = REPRO_ROOT.parent
CODEGEN_DIR = REPO_ROOT / "DT" / "codeGen"
FRAMEWORK_DIR = REPRO_ROOT / "framework"
TOOLS_DIR = REPRO_ROOT / "tools"
MANIFEST_PATH = REPRO_ROOT / "manifest.json"
STATE_PATH = REPRO_ROOT / "campaign_state.json"
AUDIT_PATH = REPRO_ROOT / "audit.json"
EVALUATOR_DIR = REPRO_ROOT / "evaluator"
MODEL_RUNTIME_DIR = REPRO_ROOT / "model_runtime" / "modelDeployer"
TEST_SCRIPT = EVALUATOR_DIR / "test_podman.sh"
MODEL_BASE_URL = os.environ.get("CODEWM_MODEL_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ARCHITECTURE_BASE_URL = os.environ.get("CODEWM_ARCHITECTURE_BASE_URL", "").rstrip("/")
ARCHITECTURE_MODEL = os.environ.get("CODEWM_ARCHITECTURE_MODEL", "")
ARCHITECTURE_MAX_TOKENS = int(os.environ.get("CODEWM_ARCHITECTURE_MAX_TOKENS", "16384"))
ARCHITECTURE_REPAIR_LLM_OUTPUT = os.environ.get(
    "CODEWM_ARCHITECTURE_REPAIR_LLM_OUTPUT", "0"
).strip().lower() in {"1", "true", "yes", "on"}
ARCHITECTURE_REBUILD_REASON = os.environ.get(
    "CODEWM_ARCHITECTURE_REBUILD_REASON", ""
).strip()
MODEL_PATH = Path(
    "/home/zhaorz/.cache/modelscope/hub/models/Qwen/"
    "Qwen3-Coder-30B-A3B-Instruct"
)
MODEL_PYTHON = Path("/home/zhaorz/software/anaconda3/envs/Code_Watermark/bin/python")
RESULTS_JSON_PATH = REPRO_ROOT / "results.json"
RESULTS_CSV_PATH = REPRO_ROOT / "results.csv"

# Keep MetaGPT's logs, generated tool schemas, default workspace, and emergency
# serialization inside the requested reproducibility directory even for simple
# imports and diagnostics. Architecture child processes override this with a
# unit-specific root before importing MetaGPT.
os.environ.setdefault("METAGPT_PROJECT_ROOT", str(REPRO_ROOT / "metagpt_runtime"))

# The frozen framework must win over any editable MetaGPT install.
sys.path.insert(0, str(FRAMEWORK_DIR))
sys.path.insert(1, str(TOOLS_DIR))
sys.path.insert(2, str(CODEGEN_DIR))


LANGUAGE_FACTS = {
    "cpp": {
        "display": "C++17",
        "build_file": "CMakeLists.txt",
        "runtime_entry": "src/Main.cpp",
        "test_target": "tests/test_main.cpp",
        "test_command": "ctest --test-dir build --output-on-failure",
        "layout": (
            "Use include/*.h and src/*.cpp pairs for reusable modules. "
            "tests/test_main.cpp must include headers, never implementation .cpp files. "
            "Use only the C++17 standard library and CMake; do not fetch dependencies. "
            "Every header must be self-contained and list every standard-library include "
            "needed by its declarations; every source must include algorithms/types it uses."
        ),
    },
    "java": {
        "display": "Java 11",
        "build_file": "pom.xml",
        "runtime_entry": "src/main/java/Main.java",
        "test_target": "src/test/java/MainTest.java",
        "test_command": "mvn -q test",
        "layout": (
            "Use Maven and Java 11 without preview features. Main.java must be in the "
            "default package because the evaluator runs Main. Put every other project class "
            "directly under src/main/java and keep it in the default package too; do not create "
            "package subdirectories or package declarations. This deliberately avoids package/import "
            "mismatches in independently generated files. Keep core logic independent from Swing/JavaFX; "
            "prefer no GUI and no non-test external dependency. pom.xml MUST declare org.junit.jupiter:"
            "junit-jupiter with test scope and a Maven Surefire version that runs JUnit 5; MainTest.java "
            "must use JUnit Jupiter only. Repeat this exact dependency contract in the pom.xml task."
        ),
    },
    "python": {
        "display": "Python 3.10",
        "build_file": "requirements.txt",
        "runtime_entry": "Main.py",
        "test_target": "tests/test_main.py",
        "test_command": "python -m pytest -q",
        "layout": (
            "Keep Main.py as a thin entrypoint and put reusable modules in a lowercase "
            "snake_case package. List pytest in requirements.txt and avoid other external "
            "dependencies unless essential. Target Python 3.10 exactly: do not use "
            "typing.Self, StrEnum, exception groups, or other Python 3.11+ APIs. Design an "
            "acyclic import graph: foundational types/errors may not import engines, entrypoints, "
            "or demos; __init__.py may export only symbols actually defined by submodules."
        ),
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Unified exec sessions may share the filesystem while each has its own PID
    # namespace (and therefore the same apparent PID). Include a random nonce
    # so concurrent model shards cannot rename each other's temporary file.
    tmp = path.with_name(
        "{}.{}.{}.tmp".format(path.name, os.getpid(), secrets.token_hex(8))
    )
    try:
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ignored_tree_part(part: str) -> bool:
    return part in {
        ".git",
        "DTResults",
        "__pycache__",
        ".pytest_cache",
        "build",
        "target",
    }


def tree_manifest(root: Path) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    if not root.exists():
        return entries
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root)
        if any(ignored_tree_part(part) for part in rel.parts):
            continue
        entries.append(
            {
                "path": rel.as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return entries


def tree_hash(root: Path) -> str:
    encoded = json.dumps(
        tree_manifest(root), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256_bytes(encoded)


def run_capture(
    command: Sequence[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            list(command),
            cwd=str(cwd) if cwd else None,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
        )
        return {
            "command": list(command),
            "return_code": result.returncode,
            "output": result.stdout,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", "replace")
        return {
            "command": list(command),
            "return_code": 124,
            "output": output,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "timeout": timeout,
        }
    except FileNotFoundError as exc:
        return {
            "command": list(command),
            "return_code": 127,
            "output": "{}: {}".format(exc.__class__.__name__, exc),
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }


def http_json(path: str, timeout: int = 10) -> Dict[str, Any]:
    request = urllib.request.Request(MODEL_BASE_URL + path)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def manifest() -> Dict[str, Any]:
    return load_json(MANIFEST_PATH)


def all_units() -> List[Dict[str, Any]]:
    data = manifest()
    units: List[Dict[str, Any]] = []
    for project in data["projects"]:
        for language in data["languages"]:
            unit_id = "p{:02d}_{}_{}".format(
                int(project["project_id"]), project["slug"], language
            )
            units.append(
                {
                    **project,
                    "language": language,
                    "unit_id": unit_id,
                    "project_name": unit_id,
                }
            )
    return units


def unit_by_id(unit_id: str) -> Dict[str, Any]:
    for unit in all_units():
        if unit["unit_id"] == unit_id:
            return unit
    raise SystemExit("Unknown unit: {}".format(unit_id))


def unit_dir(unit: Dict[str, Any]) -> Path:
    stem = "p{:02d}_{}".format(int(unit["project_id"]), unit["slug"])
    return REPRO_ROOT / "units" / stem / unit["language"]


def architecture_dir(unit: Dict[str, Any]) -> Path:
    return unit_dir(unit) / "architecture"


def team_dir(unit: Dict[str, Any]) -> Path:
    return architecture_dir(unit) / "team"


def initial_project_dir(unit: Dict[str, Any]) -> Path:
    return unit_dir(unit) / "initial_repository" / unit["project_name"]


def accepted_dir(unit: Dict[str, Any]) -> Path:
    return unit_dir(unit) / "accepted"


def replays_dir(unit: Dict[str, Any]) -> Path:
    return unit_dir(unit) / "replays"


def replay_dirs(unit: Dict[str, Any]) -> List[Path]:
    root = replays_dir(unit)
    if not root.exists():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir())


def next_replay_number(unit: Dict[str, Any]) -> int:
    numbers: List[int] = []
    for path in replay_dirs(unit):
        prefix = path.name.split("_", 1)[0]
        if prefix.isdigit():
            numbers.append(int(prefix))
    return max(numbers, default=0) + 1


def required_files(language: str) -> List[str]:
    facts = LANGUAGE_FACTS[language]
    return [facts["build_file"], facts["runtime_entry"], facts["test_target"]]


def build_architecture_prompt(unit: Dict[str, Any]) -> str:
    facts = LANGUAGE_FACTS[unit["language"]]
    targets = unit["targets"]
    features = "\n".join("- {}".format(item) for item in unit["features"])
    unit_specific_constraints = ""
    if unit["unit_id"] == "p01_snake_game_cpp":
        unit_specific_constraints = """


Project-specific C++ compilation contract:
- include/Types.h is the sole definition site for Position and Direction; every header that mentions either type must include \"Types.h\" directly
- include/IRandom.h declares both IRandom and DefaultRandom; src/Random.cpp must include \"IRandom.h\" exactly and must never include or refer to a nonexistent Random.h
- include/IRandom.h must directly include <cstddef>, <cstdint>, and <random>; spell size types std::size_t and seed types std::uint32_t because std::mt19937 is a declared data member
- include/Game.h must directly include \"Board.h\", \"IRandom.h\", \"Snake.h\", and \"Types.h\" plus <cstddef>, <deque>, and <optional>; forward declarations and transitive includes are forbidden for these dependencies
- in both Full API specification and Logic Analysis, the include/IRandom.h entry must literally enumerate `#include <cstddef>`, `#include <cstdint>`, and `#include <random>`, and the include/Game.h entry must literally enumerate `#include "Board.h"`, `#include "IRandom.h"`, `#include "Snake.h"`, `#include "Types.h"`, `#include <cstddef>`, `#include <deque>`, and `#include <optional>`
- every header must directly include every standard type it declares, including <deque>, <optional>, <set>, or <vector> when used; do not rely on transitive includes
- Game must construct its non-default-constructible Snake member in the constructor initializer list; do not default-construct and later assign it
- use the exact collision-query signature bool wouldSelfCollide(const Position& next, bool grow) const (or omit that helper entirely); no function may refer to a grow variable that is absent from its parameters or local declarations
- specify an exact Game constructor initializer containing snake_(Position{static_cast<int>(width / 2), static_cast<int>(height / 2)}, Direction::Right, 3); constructor-body assignment is forbidden, and dimensions must be validated before any game tick
- each target_compile_options flag in CMake must be a separate list argument, never one quoted string containing multiple flags
- repeat these exact filename, literal include-line, collision-signature, constructor-initializer, and CMake rules in the Full API specification, Logic Analysis, Shared Knowledge, and every affected implementation task; a generic statement that headers are self-contained is insufficient
"""
    elif unit["unit_id"] == "p01_snake_game_python":
        unit_specific_constraints = """


Project-specific Python 3.10 correctness contract:
- never import or use typing.Self, typing_extensions.Self, StrEnum, or any Python 3.11 API; every module whose annotations refer to its own classes must start with from __future__ import annotations, or quote every forward reference
- snake_game/direction.py is the sole owner of Direction; define Direction(Enum) values as exact (dx, dy) integer tuples and expose delta(self) -> tuple[int, int] plus is_opposite(self, other: Direction) -> bool
- snake_game/grid.py defines only an immutable/hashable Position and validated Grid bounds; it must never mention or import Direction and must not define Grid.delta
- snake_game/snake.py imports Direction and Position directly; next_head() obtains dx, dy from self.direction.delta() and returns Position(head.x + dx, head.y + dy)
- collision.py operates only on explicit Position/Grid/body arguments and must not duplicate direction-to-delta mapping; keep the import graph direction -> none, grid -> none, snake -> direction+grid, collision -> grid, food -> grid+random_provider, game -> the preceding modules
- use one canonical mutable Snake API consistently: turn(requested) -> bool, next_head() -> Position, and advance(grow: bool) -> None; Game and tests must not expect Snake.move to return a new object
- Game has exact constructor Game(grid: Grid, rng: RandomProvider, start: Position, direction: Direction), initializes a live game immediately, and exposes turn, step, reset, state, is_over, and score_get without a second mandatory initialization call
- step computes next_head once, checks wall and self collision before mutation, treats moving into the departing tail as safe when not growing, advances once, increments score only on food, and places new food only after consumption
- state returns exactly width, height, snake, food, score, over, and direction; snake and food coordinates are (x, y) tuples and direction is the enum name string
- Main.py defines main(), creates a deterministic provider and valid Game, performs at most two safe steps, prints one snapshot, exits, and runs main() only under the __name__ guard
- tests contain 2--4 concise deterministic cases and import every symbol they use; no wildcard imports and no test may rely on an unimported Direction
- the no-growth fixture is exact: grid 10x10, start Position(5,5), direction RIGHT, deterministic food Position(1,1), one step yields snake tuple [(6,5)], unchanged food (1,1), score 0, and over False
- the growth fixture is exact: grid 10x10, start Position(5,5), direction RIGHT, deterministic food sequence Position(6,5) then Position(1,1); one step yields snake tuples [(6,5),(5,5)], new food (1,1), score 1, and over False
- never assert growth in the no-growth fixture, never inspect private attributes such as game._snake, and do not make runtime-output formatting part of a domain-rule assertion
- repeat the exact Python 3.10, Direction.delta, Grid non-dependency, Snake mutation, Game constructor, flat state schema, deterministic fixtures, and import rules in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, and every affected implementation task; vague compatibility or acyclic-import statements are insufficient
"""
    elif unit["unit_id"] == "p02_flappy_bird_game_java":
        unit_specific_constraints = """


Project-specific Java deterministic physics and test contract:
- use screen coordinates consistently: x increases rightward and y increases downward; gravity is exactly +0.5 per tick, an upward flap velocity is exactly -8.0, and maximum speed magnitude is 10.0
- Bird(double startY) begins at y=startY and vy=0.0; applyGravity() performs vy=clamp(vy+0.5,-10.0,10.0), integrate() performs y+=vy, and flap() replaces vy with -8.0 rather than adding -8.0 to the old velocity
- Game(long seed) delegates to Game(seed,400.0,600.0,100), begins RUNNING with bird y=worldHeight/2.0, and contains zero pipes until the documented spawn interval elapses
- one running tick must call Bird.applyGravity() and then Bird.integrate(); collision must be tested on the resulting unclamped position, so Game.tick must not clamp the bird back inside the world before CollisionDetector.hitBounds can report a terminal boundary hit
- Game uses the exact public methods boolean tick(), void reset(long seed), void flapBird(), double birdY(), double birdVy(), long ticks(), int score(), and java.util.List<PipePair> pipes(); do not alternate between Bird-returning snapshots, void tick, flap, or other aliases
- RNG must store the constructor seed in a final long originalSeed field; seed() returns originalSeed without consuming or changing java.util.Random state, while nextDouble() and nextInt(int bound) delegate directly to the stored java.util.Random
- Game's RNG field is private RNG rng without final because reset(long seed) must assign rng=new RNG(seed); the delegating constructor must initialize final configuration fields and call reset(seed), and must not first assign a final RNG that reset then tries to reassign
- ScoreSystem.passedPipe(double birdX, PipePair pipe) is the independently testable scoring rule: it returns true exactly once when pipe.x()+pipe.width()<birdX and calls pipe.markScored(); Game checks scoring before removing off-screen pipes
- MainTest contains exactly 2--4 short deterministic tests and never indexes an initially empty pipe list; use ScoreSystem with a handcrafted PipePair for scoring instead of waiting for a spawn
- the exact physics fixture is: new Game(12345L) has birdY 300.0 and birdVy 0.0; one tick yields birdVy 0.5 and birdY 300.5; after reset(12345L), flap yields -8.0, then one tick yields birdVy -7.5 and birdY 292.5
- the exact RNG fixture creates RNG a and RNG b with seed 98765L, calls a.seed() twice before any random draw, then compares a.nextDouble() with b.nextDouble() and a.nextInt(100) with b.nextInt(100); never consume a random value from only one instance and later claim the streams are at the same position, and never assert two successive random values must differ
- the exact scoring fixture creates PipePair(100.0,50.0,100.0,150.0,3.0): passedPipe(149.0,pipe) and passedPipe(150.0,pipe) are false because the trailing edge is 150.0 and the comparison is strict; passedPipe(151.0,pipe) is true and marks scored; a later passedPipe(160.0,pipe) is false
- use exact collision signatures hitBounds(Bird bird,double birdHeight,double worldHeight) and hitPipe(Bird bird,double birdWidth,double birdHeight,PipePair pipe,double worldHeight); top-pipe vertical overlap is bird.y()<pipe.gapY() && bird.y()+birdHeight>0.0, while bottom overlap is bird.y()<worldHeight && bird.y()+birdHeight>pipe.gapY()+pipe.gapHeight(); never compare a y coordinate with pipe.x()
- Game.tick first calls hitBounds(bird,30.0,worldHeight) alone, then iterates for (PipePair pipe : pipes) and calls hitPipe(bird,30.0,30.0,pipe,worldHeight) on that one pipe; passing pipes, a List<PipePair>, to the single-PipePair parameter is forbidden and no list overload may be invented
- tick count starts at zero; each successful tick increments ticks exactly once and only then spawns when ticks % spawnInterval == 0, so the default game remains pipe-free for ticks 0 through 99 and first spawns on completed tick 100
- Main must call game.tick() as a standalone statement and ignore its boolean result before printing getters; it must never embed game.tick() in concatenation, formatting, assignment, or any value expression
- assertions and messages must agree with screen coordinates: downward motion means a larger y and upward motion means a smaller y; never assert that gravity makes y smaller or velocity more negative
- repeat the exact Game API, mutable Game RNG field/reset construction, coordinate convention, numeric constants, replacement flap, tick order, per-pipe collision loop and formulas, non-consuming RNG seed and paired-stream fixture, empty initial pipe list and tick-100 spawn, strict-boundary scoring fixture, standalone Main tick call, and exact physics fixture in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, and every affected implementation task
"""
    elif unit["unit_id"] == "p03_game_2048_java":
        unit_specific_constraints = """


Project-specific Java correctness contract:
- Board is the sole owner of one authoritative 4x4 int grid; getGridCopy() returns a deep read-only snapshot, so Game and spawners must never try to mutate the board through getGridCopy()
- declare one exact mutation API void setCell(int row, int col, int value) with bounds checks and 0-or-power-of-two validation, and use it consistently for deterministic setup and applying every Spawn; do not invent setGridValue, placeTile, setTile, or aliases
- declare boolean hasTileAtLeast(int value) on Board and use that exact name for win detection; do not invent hasValueAtLeast or aliases
- declare a simple immutable MoveResult with exact accessors boolean changed() and int scoreGained(); Board.move(Direction) returns it, and Game must use these methods rather than fields
- Board.move must implement each row/column by reading exactly four values in movement order, compacting nonzero values, merging one equal adjacent pair at most once, compacting/filling with zero, writing all four results back to the authoritative grid, and summing each newly merged tile into scoreGained; forbid generic multi-delta helpers with unused or ambiguous row/column parameters
- Game.move(Direction) calls Board.move once, adds scoreGained, and spawns exactly one tile only when changed() is true; apply the Spawn via Board.setCell, never via a copied array
- Game must update status after every move attempt, including an unchanged move: WON iff Board.hasTileAtLeast(2048), otherwise LOST iff !Board.hasAnyMoves(), otherwise IN_PROGRESS
- initialization/reset must clear the authoritative Board and apply exactly two spawns through Board.setCell; a deterministic SequenceSpawner must consume its documented sequence in order
- keep MainTest to 2--4 concise deterministic tests using only the canonical methods; do not assert mutations made to arrays returned by getGridCopy()
- repeat the exact getGridCopy immutability, setCell, hasTileAtLeast, MoveResult, line-merge, spawn-on-change, and status-transition rules in Full API specification, Logic Analysis, Shared Knowledge, and every affected implementation task; vague descriptions are insufficient
"""
    elif unit["unit_id"] == "p04_caro_game_java":
        unit_specific_constraints = """


Project-specific Java Caro state-machine and deterministic-test contract:
- use freestyle Gomoku semantics on a square board: five or more contiguous stones wins immediately; WinDetector.hasFiveInRow(Board,int,int,Player) must count the just-played stone plus matching stones in both signs of exactly (0,1), (1,0), (1,1), and (1,-1)
- the canonical Game API is exactly Game(int size), Board getBoard(), Player getCurrentPlayer(), GameState getState(), boolean placeMove(int row,int col), boolean undo(), void reset(), and java.util.List<Move> getHistory(); Game(int size) rejects size<5 with IllegalArgumentException and every new or reset game starts with Player.X
- placeMove has no Player argument: while IN_PROGRESS it returns false without mutation for an out-of-bounds or occupied cell; otherwise it places currentPlayer, appends exactly one Move, evaluates win then draw, and advances to currentPlayer.next() only when the resulting state remains IN_PROGRESS; after a win currentPlayer therefore remains the winner, and every terminal call returns false without mutation
- GameState uses exactly Status.IN_PROGRESS, Status.DRAW, Status.X_WON, and Status.O_WON; GameState.won(Player.X) produces X_WON and winner X, GameState.won(Player.O) produces O_WON and winner O, while inProgress/draw have an empty winner
- undo returns false without mutation when history is empty; otherwise it removes exactly the latest move, clears that board cell, restores currentPlayer to the removed move's player, restores GameState.inProgress(), and returns true
- reset clears every board cell and the complete history, restores currentPlayer=Player.X and GameState.inProgress(); it must never derive the first player from the pre-reset current turn
- Board uses one empty-cell representation consistently; isEmpty and clearCell must agree with it, snapshot returns a deep copy, and getHistory/asReadOnly return unmodifiable copies or views
- Main.main must finish by normal method return after at most one concise print; System.exit, Runtime.getRuntime().exit/halt, infinite loops, input, GUI, and background threads are forbidden because MainTest invokes Main.main inside the Surefire JVM
- MainTest.java contains exactly three concise JUnit Jupiter tests and no invented sequences: (1) Main.main(new String[0]) returns normally; (2) the exact horizontal win sequence below; (3) the exact invalid-move, undo, and reset fixture below; vertical/diagonal/draw are implementation requirements but MUST NOT add long alternative test fixtures
- the sole win fixture is literally on one new Game(15): (7,3),(0,0),(7,4),(0,2),(7,5),(0,4),(7,6),(0,6),(7,7); execute this sequence exactly once, assert all nine placeMove calls true, then status X_WON, winner Optional.of(Player.X), currentPlayer Player.X, and history size 9; do not construct a second game to replay prefixes, do not directly call WinDetector from MainTest, and never assert that the ninth move or WinDetector at (7,7) is false; no tenth move is attempted except one terminal placeMove asserted false with no mutation
- the sole state fixture is literally: new Game(15) starts X; placeMove(1,1) is true and changes turn to O; repeated placeMove(1,1) and placeMove(-1,0) are false and leave turn O/history size 1; placeMove(2,2) is true and changes turn to X; undo is true, makes (2,2) empty, restores turn O, leaves history size 1 and IN_PROGRESS; reset restores X, empty (1,1), empty history, and IN_PROGRESS; never expect O immediately after reset
- for architecture validation, the task document must literally preserve the compact sequence `(7,3),(0,0),(7,4),(0,2),(7,5),(0,4),(7,6),(0,6),(7,7)`, must say `exactly three` tests, and must mention both `placeMove(1,1)` and `placeMove(2,2)`; the phrase "nine consecutive X moves" or any test loop that lets X occupy every move is forbidden
- pom.xml must use Java 11, JUnit Jupiter test scope, and a JUnit-5-capable Surefire plugin; every class remains in the default package with no package declaration
- repeat the exact Game API, X-first/reset rule, toggle-only-while-in-progress rule, undo semantics, four-direction two-sided count, single nine-move win sequence, normal-return/no-System.exit rule, three-test limit, and literal state fixture in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, and every affected implementation task; vague statements about alternation, wins, or reset are insufficient
"""
    elif unit["unit_id"] == "p04_caro_game_python":
        unit_specific_constraints = """


Project-specific Python Caro correctness contract:
- use freestyle Gomoku semantics: five or more contiguous stones wins immediately; has_five_or_more must compute 1 + counts in both signs for each of exactly (0,1), (1,0), (1,1), and (1,-1)
- CaroGame.move(row, col) has no player argument, always places current_player, appends exactly one Move, and toggles player only when the resulting state remains IN_PROGRESS
- validation precedence is exact: if status is not IN_PROGRESS raise GameOverError before coordinate or occupancy checks; otherwise out-of-bounds or occupied cells raise InvalidMoveError without changing board, turn, history, status, or winner
- do not describe or test a wrong-player error because the canonical move API has no player argument
- the canonical horizontal-win test sequence is exactly X:(7,3), O:(0,0), X:(7,4), O:(0,2), X:(7,5), O:(0,4), X:(7,6), O:(0,6), X:(7,7); X wins on the ninth move and no earlier move produces a five-in-a-row
- tests must stop the winning sequence immediately after the ninth move; after terminal state test only GameOverError, while occupied/out-of-bounds InvalidMoveError cases must be tested on a separate IN_PROGRESS game before any win
- tests contain 2--4 concise cases, use pytest.raises with explicitly imported InvalidMoveError and GameOverError, and never catch broad Exception merely to compare class names
- reset recreates an empty board of the same size, clears history/winner, restores IN_PROGRESS, and restores the constructor's first player
- Main.py may use the same exact nine-move sequence, then prints once and exits; it must never attempt a tenth move
- repeat the exact five-or-more calculation, validation precedence, nine-move sequence, error tests, reset, and terminal behavior in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, and every affected implementation task
"""
    elif unit["unit_id"] == "p05_brick_breaker_game_cpp":
        unit_specific_constraints = """


Project-specific C++ compilation contract:
- every declaration and definition of Level::remaining and GameEngine::remainingBricks uses `std::size_t`, never unqualified `size_t`; include/Level.h and include/GameEngine.h each directly contain `#include <cstddef>`
- src/Level.cpp and src/GameEngine.cpp spell the matching return definitions as `std::size_t`; declarations and definitions must match exactly
- src/GameEngine.cpp directly contains `#include "Collision.h"` before using Collision, directly contains `#include <cmath>`, and spells square root as `std::sqrt`; do not rely on GameEngine.h or transitive includes for Collision or cmath
- keep all public types in namespace breakout consistently; Collision is the `breakout::Collision` struct declared in include/Collision.h, and GameEngine code inside namespace breakout calls that same type without inventing a different namespace or free-function API
- repeat the literal `#include <cstddef>`, `std::size_t`, `#include "Collision.h"`, `#include <cmath>`, and `std::sqrt` rules in Full API specification, Logic Analysis, Shared Knowledge, and the affected Level/GameEngine tasks so seeded generation cannot omit them
"""
    elif unit["unit_id"] == "p05_brick_breaker_game_python":
        unit_specific_constraints = """


Project-specific Python import-graph contract:
- use exactly these files: requirements.txt, brick_breaker/config.py, brick_breaker/ball.py, brick_breaker/paddle.py, brick_breaker/brick.py, brick_breaker/level.py, brick_breaker/collision.py, brick_breaker/game.py, brick_breaker/__init__.py, Main.py, tests/test_main.py
- brick_breaker/config.py is the sole definition site for GameConfig; its task and Full API entry must literally contain `brick_breaker/config.py: class GameConfig`
- brick_breaker/level.py must literally use `from .config import GameConfig`; it must never import brick_breaker.game or `.game`, at runtime or under TYPE_CHECKING
- brick_breaker/game.py must literally use `from .config import GameConfig` and may import make_grid_level from level.py; config.py must import no project module, so the graph config -> entities/level -> collision/game is acyclic
- brick_breaker/__init__.py re-exports GameConfig from `.config`, not from `.game`; Main.py and tests import public names from brick_breaker
- repeat the exact file list, sole GameConfig ownership, both literal `.config` import lines, and the prohibition on level importing game in Full API specification, Logic Analysis, Shared Knowledge, and every config/level/game implementation task
"""
    elif unit["unit_id"] == "p05_brick_breaker_game_java":
        unit_specific_constraints = """


Project-specific Java collision fixture and testability contract:
- use screen coordinates consistently: x increases rightward, y increases downward, negative vy is upward, and positive vy is downward
- Paddle's x value is the horizontal CENTER, not its left edge: getX() returns that center, asRect() has left edge x-width/2.0, and setX clamps the center to [width/2.0,maxX-width/2.0]; for Paddle(100.0,180.0,80.0,10.0,200.0), getX() is exactly 100.0 and asRect() spans x=60.0 through 140.0
- Game has the exact injectable constructor Game(double width, double height, Paddle paddle, Ball ball, java.util.List<Brick> bricks, int lives); it defensively copies the list but retains the supplied Ball, Paddle, and Brick object identities so deterministic tests can observe mutation
- Game declares the life counter exactly as private int lives; final, effectively immutable, shadow, record, or alternate life counters are forbidden; the constructor assigns this.lives = lives and getLives() returns that same mutable field
- bottom-out handling is exact: when ball.getY()+ball.getRadius()>=height and lives>0, execute lives -= 1 exactly once, set lifeLost=true, reset the retained ball to x=paddle.getX() and y=paddle.getY()-ball.getRadius()-1.0, and make its vertical velocity negative; an implementation that only sets lifeLost without decrementing lives is forbidden
- getBricks() returns an unmodifiable view or copy and tests must never mutate that result to configure the game; tests needing one brick must invoke the injectable constructor with java.util.List.of(brick), never call createDemoLevel() and then assert or try to force a one-brick layout
- Ball exposes package-private setPosition(double x,double y) and setVelocity(double vx,double vy), accessible to the sole default-package MainTest; Brick.hit() decrements a breakable brick by exactly one to a minimum of zero
- tick(dt) validates finite dt>0, integrates x+=vx*dt and y+=vy*dt once, handles left/right/top walls, paddle, then bricks; a colliding brick is hit exactly once in that tick, a destroyed breakable brick is removed and adds exactly 100 score once, and levelCompleted becomes true exactly when the retained bricks list is empty
- circle/rectangle contact is inclusive: nearest-point squared distance <= radius squared is a collision; resolve on the minimum-penetration axis and reflect the corresponding velocity component
- the exact one-brick fixture is: width=200.0, height=200.0; Paddle(100.0,180.0,80.0,10.0,200.0); Ball(60.0,45.0,0.0,10.0,5.0); Brick(new Rect(50.0,50.0,20.0,10.0),1,true); lives=3; after tick(0.1), the same brick has 0 hit points, getBricks() is empty, score is 100, and levelCompleted is true
- the exact life-loss fixture uses the same dimensions and paddle, Ball(100.0,199.0,0.0,20.0,5.0), an unbreakable Brick(new Rect(0.0,20.0,20.0,10.0),1,false), and 3 lives; after tick(0.5), lives is 2, lifeLost is true, ball x is 100.0, ball y is 174.0, ball vy is negative, and levelCompleted is false because the unbreakable brick remains
- MainTest contains exactly three concise deterministic tests: Main.main smoke, the exact injected one-brick fixture, and the exact injected life-loss fixture; the two domain tests MUST copy every numeric constructor argument and dt above literally, with no alternate dimensions, positions, velocities, radius, paddle, brick, or time step
- MainTest's life test must literally assert assertEquals(2,game.getLives()), assertTrue(game.isLifeLost()), assertEquals(100.0,ball.getX(),1e-9), assertEquals(174.0,ball.getY(),1e-9), assertTrue(ball.getVy()<0.0), and assertFalse(game.isLevelCompleted()); approximate phrases such as "positioned to cross" are insufficient and alternative fixtures are forbidden
- MainTest's brick test must literally use the stated 200.0-world fixture and tick(0.1), then assert the same Brick identity has zero hit points, game.getBricks().isEmpty(), score 100, and levelCompleted true; createDemoLevel and any substituted fixture are forbidden in this test
- retained Brick identity means only that the caller's original `brick` reference observes brick.getHitPoints()==0 after Game mutates and removes it; after removal the brick list MUST NOT contain that object, so the test must use assertFalse(game.getBricks().contains(brick)); asserting both isEmpty() and contains(brick), or otherwise asserting contains(brick) after removal, is explicitly forbidden
- the Game.java task and Full API must spell the reset expression as ball.setPosition(paddle.getX(),paddle.getY()-ball.getRadius()-1.0); examples using -0.1, paddle.getX()+paddle.getWidth()/2.0, a preserved old ball x, or any alternative formula are forbidden
- repeat the exact constructor, center-based Paddle semantics, mutable private int lives field, mandatory lives -= 1 bottom-out statement and reset coordinates, retained entity identity observed through the external brick reference, mandatory assertFalse after brick removal, read-only brick list, tick order, inclusive collision, score/removal rule, bricks-empty completion rule, coordinate convention, literal test assertions, and both numeric fixtures in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, and every affected implementation task
"""
    elif unit["unit_id"] == "p06_tank_battle_game_java":
        unit_specific_constraints = """


Project-specific Java Tank Battle compilation and deterministic-fixture contract:
- use exactly these files and no substitutes: pom.xml, src/main/java/Position.java, src/main/java/Orientation.java, src/main/java/Command.java, src/main/java/Tank.java, src/main/java/Projectile.java, src/main/java/ObstacleMap.java, src/main/java/Arena.java, src/main/java/ScoreBoard.java, src/main/java/GameEngine.java, src/main/java/Main.java, src/test/java/MainTest.java; every class is in the default package and no package declaration is allowed
- pom.xml targets Java 11, declares JUnit Jupiter in test scope, and configures a JUnit-5-capable Maven Surefire plugin; Main.main is non-interactive, prints at most one concise snapshot, and returns normally without System.exit, GUI, input, network, loops, or threads
- Position is an immutable value Position(int x,int y) with getX(), getY(), translate(int dx,int dy), value-based equals, and hashCode; Orientation is an enum NORTH(0,-1), EAST(1,0), SOUTH(0,1), WEST(-1,0) with dx(), dy(), left(), and right(); Command is exactly an enum with MOVE_FORWARD, TURN_LEFT, TURN_RIGHT, and FIRE
- Tank has Tank(String id,Position position,Orientation orientation,int health), validates nonblank id/non-null values and permits health==0 so dead tanks can be copied but rejects health<0; it has mutable fields `private Position position;`, `private Orientation orientation;`, and `private int health;`; expose getId/getPosition/getOrientation/getHealth/isAlive, package-private setPosition(Position), rotateLeft(), rotateRight(), applyDamage(int), and copy(); copy() must work when health is zero, while position and orientation must not be final because movement and rotation mutate them
- Projectile has Projectile(String shooterId,Position position,Orientation orientation), mutable `private Position position;`, getShooterId/getPosition/getOrientation, package-private `void setPosition(Position position)`, and copy(); GameEngine may move a projectile only through that declared setPosition method and must never call an undeclared projectile mutator
- ObstacleMap.empty(), add(Position), isBlocked(Position), and copy() use a set of immutable Position values; Arena(int width,int height,ObstacleMap obstacles) validates positive dimensions, defensively copies obstacles, and exposes inBounds(Position), isObstacle(Position), and copy()
- ScoreBoard(Collection<String> tankIds) owns private hit and kill maps initialized to zero for every id; expose addHit(String), addKill(String), getHits(String), getKills(String), getScore(String)=hits+5*kills, asMap(), copy(), and `void reset(Collection<String> tankIds)`; GameEngine.reset must call scoreBoard.reset(initialTanks.keySet()) and must never access ScoreBoard fields directly, assign to its private maps, or replace a final scoreBoard field
- GameEngine has the exact reset-compatible ownership fields `private Arena arena;`, `private final Arena initialArena;`, `private Map<String,Tank> tanks;`, `private final Map<String,Tank> initialTanks;`, and `private final ScoreBoard scoreBoard;`. `tanks` is the only mutable current-state tank map; `initialTanks` is an immutable-by-convention deep snapshot and MUST NEVER be cleared, mutated, or used as the current-state map. The current arena is deliberately not final because reset assigns exactly `this.arena = initialArena.copy();`; initialArena, initialTanks, and scoreBoard remain final. GameEngine(Arena arena,List<Tank> tanks) requires at least two initially alive tanks (health>0) with unique ids on distinct in-bounds non-obstacle cells, deep-copies the supplied arena, and initializes one empty FIFO command queue per tank; expose enqueue(String tankId,Command), tick(), reset(), getTanksCopy(), getProjectilesCopy(), getScoreBoardCopy(), getArena(), and winner()
- inside the GameEngine constructor, every supplied tank MUST be copied into two independently allocated objects with these literal statements in this order: `Tank initialCopy = tank.copy();`, `Tank currentCopy = tank.copy();`, `this.initialTanks.put(tank.getId(), initialCopy);`, and `this.tanks.put(tank.getId(), currentCopy);`. Reusing one `copy`, `copied`, or other Tank object in both maps is forbidden, as is deriving currentCopy from a mutable object already stored in either map
- GameEngine never uses Java Stream API, `.stream()`, or `Collectors`; no file imports java.util.stream. Its reset calls the literal `scoreBoard.reset(initialTanks.keySet())` directly. Every java.util symbol used by a file is either directly imported or fully qualified; Main uses `java.util.Arrays.asList(...)` fully qualified and never refers to bare Arrays without an import
- each tick processes at most one queued command for each live tank in lexicographic tank-id order, then updates projectiles; MOVE_FORWARD tries exactly one orientation cell and stops on bounds/obstacle/another live tank, turns mutate orientation, and FIRE spawns at the forward cell only when it is in bounds and not an obstacle
- during that same tick, every projectile advances exactly one orientation cell using Projectile.setPosition and is then removed on bounds/obstacle or on hitting the first non-owner live tank at that cell; a hit applies one damage, calls addHit(shooterId), calls addKill(shooterId) only when health becomes zero, and consumes the projectile; dead tanks do not execute commands or block movement
- enqueue, tick, movement, fire/hit resolution, winner, and getTanksCopy operate only on the current `tanks` map and never on initialTanks. reset assigns `this.arena = initialArena.copy();`, assigns `this.tanks = new HashMap<>();`, then restores tank copies into `this.tanks` by iterating `initialTanks.values()` without streams; it never calls initialTanks.clear() or initialTanks.put(...), recreates empty command queues, clears projectiles, and calls `scoreBoard.reset(initialTanks.keySet())`; getTanksCopy/getProjectilesCopy/getScoreBoardCopy return fresh defensive copies and tests must fetch a fresh tank copy after every tick rather than retaining a stale prior copy
- winner returns the sole surviving tank id only when exactly one of the at-least-two initial tanks is alive, otherwise null
- MainTest.java contains exactly three concise JUnit Jupiter tests: (1) Main.main(new String[0]) returns normally; (2) blocked movement plus reset uses Arena(6,5,obstacles), Alice at (1,2) EAST health3, Bob at (4,2) WEST health3, an obstacle at Position(2,2), verifies a freshly fetched Alice from `engine.getTanksCopy()` remains (1,2), fetches Alice again after TURN_RIGHT and verifies SOUTH, calls reset, fetches Alice again and verifies EAST and health3, then verifies zero score and no projectiles; (3) hit/kill uses empty Arena(6,5), Alice at Position(1,2) EAST health3 and Bob at Position(3,2) WEST health1, enqueues Alice FIRE and ticks once, then a freshly fetched Bob copy has health0, Alice has hits1/kills1/score6, projectiles are empty, and winner is Alice
- because GameEngine deep-copies constructor inputs, MainTest MUST NEVER inspect `alice`, `bob`, or any other constructor-supplied Tank after GameEngine construction to observe gameplay or reset. Every post-construction tank assertion must first locate a new object in a fresh call to `engine.getTanksCopy()`; retaining a Tank or List<Tank> across tick/reset is forbidden
- the hit fixture relies on same-tick movement from the spawned Position(2,2) to Bob at Position(3,2); never expect a hit on the shooter, never add a kill with a second shot after the target is already dead, and never assert against a List<Tank> copy captured before the tick
- repeat the exact file list, method signatures, exact GameEngine arena/initialArena/tanks/initialTanks/scoreBoard fields, the four literal two-independent-copy constructor statements, the ban on post-construction observation of input Tank objects, strict current-state-versus-snapshot ownership rule, no-stream/no-Collectors rule, qualified Arrays usage, reset assignments, mutable-field declarations, ScoreBoard.reset boundary, same-tick projectile semantics, fresh-copy rule, three-test limit, and both numeric fixtures in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, and every affected implementation task
"""
    elif unit["unit_id"] == "p06_tank_battle_game_python":
        unit_specific_constraints = """


Project-specific Python Tank Battle public-API and deterministic-fixture contract:
- the architecture Canonical File References, File list, Logic Analysis, and Task list must use exactly these files and no substitutes: requirements.txt, tank_battle/directions.py, tank_battle/geometry.py, tank_battle/obstacle.py, tank_battle/arena.py, tank_battle/tank.py, tank_battle/projectile.py, tank_battle/commands.py, tank_battle/scoring.py, tank_battle/game.py, tank_battle/configs.py, tank_battle/__init__.py, Main.py, tests/test_main.py; tank_battle/direction.py, tank_battle/entities.py, tank_battle/scoreboard.py, tank_battle/demo.py, and any combined or renamed substitute are forbidden
- tank_battle/__init__.py must explicitly import and re-export exactly these public symbols: Game, Arena, Obstacle, Rect, Tank, Projectile, ScoreBoard, Direction, Command, MoveForward, RotateLeft, RotateRight, RotateTo, Fire, and build_default_demo; __all__ lists those exact names, no wildcard import is allowed, and tests must never expect nested aliases such as Game.Arena or a package attribute named commands
- Direction is defined only in tank_battle/directions.py with the literal skeleton `from enum import Enum`, `class Direction(Enum):`, `N=(0,-1)`, `E=(1,0)`, `S=(0,1)`, and `W=(-1,0)`; delta(self)->tuple[int,int] returns self.value, left()->Direction and right()->Direction return enum members, and all movement/barrel/projectile code uses delta rather than duplicate mappings; a plain class whose members are strings or post-construction singleton objects is forbidden
- Rect is an immutable value with Rect(x:int,y:int,w:int,h:int), rejects nonpositive w/h, and contains(px,py) uses half-open cells x<=px<x+w and y<=py<y+h; Obstacle contains one Rect; Arena(width:int,height:int,obstacles:list[Obstacle]) rejects nonpositive dimensions and exposes in_bounds(x,y) and is_blocked(x,y), where out-of-bounds and obstacle cells are blocked
- Tank has the exact constructor Tank(id:str,name:str,x:int,y:int,direction:Direction,health:int=3,speed:int=1), public attributes with the name direction (never dir), barrel_ahead() using direction.delta(), alive(), and clone(); Projectile uses Projectile(pid:int,owner_id:str,x:int,y:int,direction:Direction,speed:int=1), the attribute name direction, move(), and clone()
- Command is an instantiable marker class with no ABC inheritance, no @abstractmethod, and no execute method; its concrete MoveForward, RotateLeft, RotateRight, RotateTo, and Fire subclasses also define no execute method
- Game.tick dispatches commands itself solely with isinstance(command, MoveForward/RotateLeft/RotateRight/RotateTo/Fire); command.execute(...) and every other polymorphic command-execution callback are forbidden; MoveForward(steps:int=1) rejects steps<1, RotateLeft/RotateRight/Fire take no arguments, and RotateTo(direction:Direction) stores the attribute direction
- the canonical Game constructor is Game(arena:Arena,tanks:dict[str,Tank]); it validates unique in-bounds unblocked tank cells, deep-copies and stores an immutable initial arena/tank snapshot, and exposes public arena, tanks, projectiles, scores, command_queue, next_projectile_id plus queue_command(player_id,command), tick(), reset(), winner(), and snapshot()
- deterministic tick order is exact: stable-sort queued commands by player id, apply them, clear the queue, then process projectiles by pid; MoveForward attempts one cell at a time and stops before bounds, obstacle, or another live tank; Fire spawns at barrel_ahead if that cell is free, then every projectile including a newly spawned one moves by its speed during that same tick; after each unit step it despawns on bounds/obstacle or hits the first non-owner live tank at that cell, deals exactly one health, records exactly one hit and one kill only if health becomes zero, and is removed
- reset must restore deep clones of the constructor-supplied initial arena and every initial tank including position, direction, health, and speed; it also clears projectiles and command_queue, recreates zeroed scores, and sets next_projectile_id=0; merely clearing projectiles/scores while leaving moved or damaged tanks unchanged is forbidden
- ScoreBoard has the exact constructor `ScoreBoard(player_ids:list[str])`, immediately initializes both hits and kills as `{player_id:0 for player_id in player_ids}`, exposes record_hit, record_kill, and score(player_id)=hits+5*kills; Game construction and reset each use `ScoreBoard(list(self._initial_tanks))`, so zero-hit and zero-kill entries such as kills["p1"] always exist; winner returns one surviving tank id only when at least two tanks were initially supplied and exactly one remains alive, otherwise None
- tank_battle/game.py directly imports every command class it dispatches with the literal line `from .commands import Command, MoveForward, RotateLeft, RotateRight, RotateTo, Fire`; importing only Command and then referencing undeclared subclasses is forbidden, and the six mutable public attributes arena, tanks, projectiles, scores, command_queue, and next_projectile_id must be ordinary assignable attributes rather than getter-only properties
- Fire first creates a projectile at barrel_ahead, then the same tick's projectile phase moves every projectile including that new projectile by speed one cell at a time; in the exact hit fixture, tick one therefore leaves it at (3,2), and tick two moves it to (4,2) and hits p2; a test expecting (2,2) after tick one is forbidden
- on a hit, game.py must literally call `self.scores.record_hit(projectile.owner_id)` and, only when health becomes zero, `self.scores.record_kill(projectile.owner_id)`; passing the hit tank id, target id, Tank object, or any other value is forbidden
- tank_battle/configs.py is the sole owner of build_default_demo()->Game; it constructs exactly an 8-by-5 empty Arena and two tanks: Tank("p1","P1",1,2,Direction.E,3,1) and Tank("p2","P2",6,2,Direction.W,3,1); tank_battle/__init__.py imports build_default_demo from .configs; Main.py must use the literal import `from tank_battle import build_default_demo, RotateRight`, exposes run_demo()->dict, literally calls `game.queue_command("p1", RotateRight())` (a command instance, never the string "RotateRight"), then calls `game.tick()` exactly once and returns snapshot without input/network/GUI; main() prints that one snapshot and is called only under the __name__ guard
- for architecture validation, the Full API specification must literally describe string tank/player/owner ids, `Tank(id:str,...)`, `Projectile(...,owner_id:str,...)`, `Game(arena:Arena,tanks:dict[str,Tank])`, `queue_command(self,player_id:str,...)`, `build_default_demo()->Game`, `record_hit`, `record_kill`, and `score(player_id)=hits+5*kills`; numeric tank/player/owner ids, `tanks:list[Tank]`, and any tuple return from build_default_demo are forbidden
- the Full API specification must also repeat these exact compact fixture expressions verbatim: `Arena(8,5,[])`, `Tank("p1","P1",1,2,Direction.E,3,1)`, and `Tank("p2","P2",6,2,Direction.W,3,1)`; it must explicitly say `MoveForward` rejects `steps<1`, winner returns the sole surviving tank id only when exactly one remains alive from at least two initial tanks, and run_demo queues `RotateRight` for `p1` then calls tick exactly once
- tests/test_main.py contains exactly four concise pytest tests, imports every used symbol directly from tank_battle plus run_demo from Main, and must not use Game.Arena, package.commands, private members, monkeypatching, long loops, or alternate fixtures
- tests/test_main.py uses only absolute top-level imports beginning with the literal `from tank_battle import` and `from Main import run_demo`; any leading-dot relative import is forbidden because pytest loads this file as a top-level test module
- runtime fixture: result=run_demo(); assert it is a dict with keys exactly arena,tanks,projectiles,scores,winner and result["tanks"]["p1"]["direction"]=="S"
- obstacle fixture: Arena(8,5,[Obstacle(Rect(3,1,1,1))]), p1=Tank("p1","P1",2,1,Direction.E), p2=Tank("p2","P2",6,4,Direction.W), Game(arena,{"p1":p1,"p2":p2}); queue MoveForward(2) for p1 and tick; assert game.tanks["p1"] remains at (2,1)
- hit fixture: Arena(8,5,[]), p1=Tank("p1","P1",1,2,Direction.E), p2=Tank("p2","P2",4,2,Direction.W,2,1), Game(arena,{"p1":p1,"p2":p2}); queue Fire for p1 and tick once, yielding one projectile at (3,2); tick again, yielding p2.health==1, no projectiles, hits["p1"]==1, kills["p1"]==0, score("p1")==1, and winner() is None
- reset fixture constructs a fresh Arena(8,5,[]) with p1=Tank("p1","P1",1,2,Direction.E) and p2=Tank("p2","P2",4,2,Direction.W,2,1), then immediately records `initial=game.snapshot()` before any command or tick; it must not queue Fire and must not call tick before this initial capture; only afterward it queues MoveForward(1) for p1 and ticks once, directly changes game.tanks["p2"].health=0, then reset(); assert snapshot()==initial, command_queue/projectiles empty, `game.scores.hits=={"p1":0,"p2":0}`, `game.scores.kills=={"p1":0,"p2":0}`, score("p1")==0, score("p2")==0, and next_projectile_id==0; asserting empty score dictionaries or capturing the post-hit state as initial is forbidden
- snapshot returns only newly allocated plain dict/list/scalar values: arena is a dict (never an Arena object), each tank/projectile direction is `direction.name`, scores contains plain hits/kills/score mappings, and no mutable domain object is returned; tests compare this serialized dict data and must never compare Arena/Tank/Projectile objects by identity
- repeat the exact explicit exports, attribute names direction, constructors, initialized ScoreBoard dictionaries, direct command imports, owner-id scoring calls, same-tick projectile movement, absolute test imports, full reset rule, build_default_demo layout, run_demo result, four-test limit, and all literal fixtures in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, and every affected implementation task; generic statements about a public API or deterministic reset are insufficient
"""
    elif unit["unit_id"] == "p07_calculator_python":
        unit_specific_constraints = """


Project-specific Python 3.10 calculator ownership and deterministic-test contract:
- use exactly these files and no substitutes, in dependency order: requirements.txt, calculator/errors.py, calculator/history.py, calculator/tokenizer.py, calculator/engine.py, calculator/api.py, calculator/__init__.py, Main.py, tests/test_main.py
- calculator/errors.py solely defines CalculatorError, TokenizationError, ParseError, and EvaluationError. calculator/history.py solely defines History with add(expression:str,result:float), records()->list[tuple[str,float]], and __len__(), and imports no project module
- calculator/tokenizer.py solely defines Token, NumberToken, OpToken, LParenToken, RParenToken, and Tokenizer. It may import only standard-library modules and the literal line `from .errors import TokenizationError`; it MUST NEVER import `calculator.tokenizer`, `.tokenizer`, or any symbol from itself, including under TYPE_CHECKING. The literal strings `from .tokenizer import` and `from calculator.tokenizer import` are forbidden inside calculator/tokenizer.py
- token types are real constructible classes, never aliases to object: define a marker `class Token:`, immutable NumberToken(Token) with required float value, immutable OpToken(Token) with required operator value, and zero-argument LParenToken(Token) and RParenToken(Token). `NumberToken = object`, `OpToken = object`, `Token = object`, and every similar reassignment are forbidden
- Tokenizer.tokenize(expression:str)->list[Token] ignores whitespace, emits decimal numbers and +,-,*,/ parentheses tokens, folds unary signs at the start or after an operator/left parenthesis into the immediately following number, and raises TokenizationError for invalid characters or malformed numbers. Every scan branch advances its index or returns/raises; no input loop can stall
- calculator/engine.py literally imports the token classes with `from .tokenizer import Token, NumberToken, OpToken, LParenToken, RParenToken`, imports ParseError and EvaluationError from .errors, and defines to_rpn plus eval_rpn using shunting-yard and a float stack. It never imports api or calculator.__init__
- calculator/api.py imports Tokenizer/Token from .tokenizer, to_rpn/eval_rpn from .engine, History from .history, and ParseError from .errors. evaluate(expression,history=None) rejects blank input with ParseError, evaluates deterministically, appends one history record only on success, and propagates domain exceptions; tokenize is a thin Tokenizer().tokenize wrapper
- calculator/__init__.py explicitly re-exports evaluate, tokenize, History, CalculatorError, TokenizationError, ParseError, and EvaluationError. Main.py uses the absolute import `from calculator import evaluate, History`, defines run_demo()->dict with one fixed expression and history result, prints at most one concise value under the __name__ guard, and performs no input/network/filesystem/GUI/thread work
- tests/test_main.py contains exactly three concise pytest tests using only `from calculator import evaluate, tokenize, History, CalculatorError, TokenizationError, ParseError, EvaluationError` and `from Main import run_demo`: (1) run_demo returns a dict and `evaluate("2 + 3 * 4") == 14.0`; (2) one History records exactly `("(1 + 2) * 3",9.0)` and `len(tokenize("1 + 2.5")) == 3`, with no isinstance, reflection, internal-token import, token constructor call, or expression such as `type(tokens[0])()`; (3) division by zero raises EvaluationError, `evaluate("1 @ 2")` raises TokenizationError, and blank input raises ParseError
- repeat the exact file list, sole tokenizer type ownership, both forbidden self-import strings, real token-class declarations, one-way import graph, canonical public exports, exact three tests, and the ban on token construction/type introspection in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, and every affected implementation task
"""
    elif unit["unit_id"] == "p08_excel_data_processing_java":
        unit_specific_constraints = """


Project-specific Java 11 in-memory spreadsheet processing contract:
- use exactly these files and no substitutes, in dependency order: pom.xml, src/main/java/ProcessingReport.java, src/main/java/Cell.java, src/main/java/Row.java, src/main/java/Sorters.java, src/main/java/Sheet.java, src/main/java/Workbook.java, src/main/java/ValueParser.java, src/main/java/Filters.java, src/main/java/Aggregations.java, src/main/java/CsvIO.java, src/main/java/Main.java, src/test/java/MainTest.java; all project classes are in the default package
- pom.xml targets Java 11, declares JUnit Jupiter in test scope, and configures a JUnit-5-capable Surefire plugin. Java streams are forbidden throughout this small repository, especially `Stream.toList()` which does not exist in Java 11; use ordinary bounded loops and `java.util.ArrayList`
- ProcessingReport starts rowsRead, rowsKept, and rowsWritten at zero and owns a LinkedHashMap<String,Integer> invalidCounts. incrementRowsRead/incrementRowsKept/incrementRowsWritten add exactly one; recordInvalid(column) adds exactly one for that key; getters return counters; invalidCounts returns an unmodifiable defensive LinkedHashMap copy. No method changes an unrelated counter
- Cell is immutable: Cell.of(String raw) maps null to the empty string and otherwise preserves the string; raw() returns it and isBlank() tests raw.trim().isEmpty(). Row copies its header and cells, get(String column) returns the cell at the first equal header or Cell.of("") if absent, and header(), cells(), and asStringMap() return unmodifiable defensive values
- Sorters.Order(String column,boolean ascending) exposes column() and ascending(). Sorters.comparator(List<Order>) compares Cell.raw() strings in order, puts blank values last regardless of direction, and is deterministic. Sheet copies name/header/rows, exposes name(), header(), rows(), filter(Predicate<Row>,ProcessingReport), and sort(List<Sorters.Order>); filter increments rowsKept exactly once per retained row and neither operation changes rowsRead or rowsWritten
- Workbook is only an in-memory named-sheet container with addSheet, getSheet returning Optional, and sheetNames returning an unmodifiable defensive set
- ValueParser.toDouble(String raw,String column,ProcessingReport report) trims input, returns null without recording for null/blank, returns Double.valueOf for valid input, and on invalid input calls report.recordInvalid(column) exactly once then returns null. Filters.equals and contains perform string predicates; numericGreaterThan uses ValueParser once per tested row
- Aggregations exposes count, sum, average, min, and max. Each numeric method visits every row once and calls ValueParser.toDouble exactly once for that row; blank and invalid values are ignored, sum/average return 0.0 when no numeric value, min/max return null. Therefore one invocation of sum over one invalid `bad` cell records exactly one invalid count; tests must use a fresh ProcessingReport for each independent aggregation instead of expecting several aggregation calls to record one combined invalid event
- CsvIO has exactly two public static operations: `Sheet importCsvFromString(String name, String csv, ProcessingReport report)` and `String toCsvString(Sheet sheet, ProcessingReport report)`. The format is deliberately simple comma-separated text with no quoted commas. Import treats the first line as header, preserves empty fields by using split with a negative limit, pads short data rows, ignores excess cells, and calls incrementRowsRead exactly once per data row. Export emits the header and every data row with commas and newline separators, calls incrementRowsWritten exactly once per data row, and never changes rowsRead/rowsKept. There is no report-free export overload and no Reader/Writer/filesystem API
- Main.main uses one fixed in-memory CSV string, fresh reports for logically separate operations, prints at most one concise deterministic summary, and returns normally without input, network, filesystem, GUI, threads, clock, or randomness
- Because all project classes are in the unnamed/default package, MainTest imports only org.junit.jupiter.api.Test, static org.junit.jupiter.api.Assertions members, and ordinary java.util classes; it directly refers to project classes by simple name and must never emit invalid lines such as `import Sheet;`, `import CsvIO;`, or `import ProcessingReport;`
- MainTest contains exactly three concise tests and uses no streams: (1) runtime invokes `Main.main(new String[0])` and returns normally; (2) pipeline uses the literal CSV `Name,Country,Sales\nAlice,US,1000\nBob,CA,1500\nCharlie,US,2000`, imports with reportImport and asserts rowsRead==3, filters Country US with reportFilter and asserts rowsKept==2, then MUST literally assert `assertEquals("Alice", filteredRows.get(0).get("Name").raw());` and `assertEquals("Charlie", filteredRows.get(1).get("Name").raw());`, sorts those two rows descending by Name and MUST literally assert `assertEquals("Charlie", sortedRows.get(0).get("Name").raw());` and `assertEquals("Alice", sortedRows.get(1).get("Name").raw());`, then sums Sales with a fresh reportAggregation and asserts 3000.0 and empty invalidCounts; Row itself has no raw() method, so `filteredRows.get(1).raw()` and every equivalent direct Row.raw() call are forbidden; (3) invalid/round-trip uses literal CSV `Name,Sales\nAlice,1000\nBob,bad\nCharlie,\nDana,2000`, calls sum exactly once with a fresh reportAggregation and asserts 3000.0 plus invalidCounts().get("Sales")==1, exports with a fresh reportExport and asserts rowsWritten==4, re-imports with a fresh reportReimport and asserts rowsRead==4, identical header, four rows, and Bob's Sales remains `bad`
- no test expects rowsKept immediately after import, no test expects rowsWritten after import or before calling the report-taking toCsvString, and no test reuses one ProcessingReport across sum/average/min/max while expecting only one invalid count
- repeat the exact file list, Java 11 no-stream rule, counter ownership, two-method CsvIO API, separate-report rule, default-package import ban, exact three fixtures, and exactly three test scopes in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, and every affected implementation task
"""
    elif unit["unit_id"] == "p08_excel_data_processing_python":
        unit_specific_constraints = """


Project-specific Python workbook API and acyclic-import contract:
- use exactly these files and no substitutes: requirements.txt, excel_processor/model.py, excel_processor/operations.py, excel_processor/csv_io.py, excel_processor/report.py, excel_processor/__init__.py, Main.py, tests/test_main.py
- the project import graph is strictly one-way: model.py imports no project module; operations.py, csv_io.py, and report.py may import only from .model; __init__.py imports those four modules only to re-export their public names; Main.py and tests import from excel_processor; no lower module imports __init__, Main, or another operation module, and TYPE_CHECKING imports must not create a reverse edge
- model.py is the sole definition site for Cell, Row, and Sheet. Cell(value:object=None) exposes mutable value. Row(cells:list[Cell]) defensively copies the list and exposes values()->list[object]. Sheet(rows:list[Row]) defensively copies rows and exposes classmethod from_values(values:list[list[object]])->Sheet, to_values()->list[list[object]], row_count()->int, column_count()->int, get_cell(row:int,column:int)->Cell, and set_cell(row:int,column:int,value:object)->None; from_values rejects ragged non-empty rows, and indexed operations reject negative/out-of-range indices
- operations.py defines only filter_rows(sheet:Sheet,predicate:Callable[[Row],bool])->Sheet, sort_rows(sheet:Sheet,key:Callable[[Row],object],reverse:bool=False)->Sheet, and aggregate_column(sheet:Sheet,column:int)->dict[str,object]; every result is a new Sheet with new Row/Cell objects and never mutates the input
- aggregate_column reports exactly keys count, missing, numeric_count, sum, min, max; None and the empty string are missing, numeric values exclude bool, sum is 0 when there are no numeric values, and min/max are None when there are no numeric values
- csv_io.py uses only csv and io.StringIO and defines loads_csv(text:str)->Sheet and dumps_csv(sheet:Sheet)->str; CSV cells remain strings, empty cells remain empty strings, malformed ragged CSV raises ValueError, and neither function accesses the filesystem
- report.py defines build_report(sheet:Sheet)->dict[str,object] returning exactly row_count, column_count, and missing_cells, where missing means None or the empty string
- excel_processor/__init__.py explicitly re-exports Cell, Row, Sheet, filter_rows, sort_rows, aggregate_column, loads_csv, dumps_csv, and build_report; wildcard imports and nonexistent aliases such as Filter, Sorter, ReportGenerator, or CSVUtils are forbidden
- Main.py uses the absolute import `from excel_processor import Sheet, filter_rows, sort_rows, aggregate_column, build_report`, exposes run_demo()->dict, performs a small in-memory deterministic demonstration, and main() prints at most one result under the __name__ guard; no input, filesystem, network, GUI, threads, or loops that wait for input
- tests/test_main.py contains exactly three concise pytest tests using absolute imports: (1) run_demo returns a dict; (2) Sheet.from_values([[3,"c"],[1,"a"],[2,"b"],[None,""]]) calls the literal `filter_rows(sheet, lambda row: isinstance(row.values()[0], (int, float)) and row.values()[0] >= 2)` and therefore keeps exactly [[3,"c"],[2,"b"]], a separate Sheet.from_values([[3],[1],[2]]) sorted ascending yields [[1],[2],[3]], and aggregate_column on the four-row sheet yields count4, missing1, numeric_count3, sum6, min1, max3; (3) loads_csv("name,value\\nA,1\\nB,\\n") yields exactly [["name","value"],["A","1"],["B",""]], dumps_csv round-trips through loads_csv, and build_report reports row_count3, column_count2, missing_cells1
- tests never import old-module names sheet.py, row.py, cell.py, filter.py, sort.py, csv_utils.py, or classes Filter/Sorter/ReportGenerator/CSVUtils; tests call only the canonical API above and do not inspect private attributes
- repeat the exact file list, sole model ownership, one-way import graph, canonical signatures, aggregate schema, CSV fixture, three-test limit, and literal deterministic fixtures in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, and every affected implementation task
"""
    elif unit["unit_id"] == "p09_qr_code_gen_det_cpp":
        unit_specific_constraints = """


Project-specific C++17 fixed QR-like codec contract:
- structured-output safety for this unit: every role outputs only fields listed in that current action's `nodes` schema. In particular, the Architect/Design action sets its optional `Data structures and interfaces` and `Program call flow` fields to empty strings and MUST NOT prematurely add ProjectManager-only fields such as Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, C++ Build Link Audit, or Task list. The later ProjectManager/Task action must provide all of those fields and preserve the exact API tokens below. Keep every JSON string as single-line plain prose, and emit no Mermaid, Markdown code fence, multiline code sample, literal newline inside a JSON string, or function body. This transport rule prevents invalid JSON and does not relax any repository contract
- replace the over-split architecture with exactly these files in dependency order: CMakeLists.txt, include/QRMatrix.h, src/QRMatrix.cpp, include/QRCodec.h, src/QRCodec.cpp, include/QRRenderer.h, src/QRRenderer.cpp, src/Main.cpp, tests/test_main.cpp. Do not create BinaryEncoder, QRLayout, QREncoder, QRValidator, QRDetector, namespace-only helper headers, or any additional source/test file
- CMakeLists.txt sets C++17 with extensions off, builds one qr_core library from the three non-Main source files, publishes `${CMAKE_CURRENT_SOURCE_DIR}/include`, builds qr_app from src/Main.cpp and qr_tests from tests/test_main.cpp, links both to qr_core, calls enable_testing(), and registers qr_tests with add_test. No external package, FetchContent, network, image, GUI, or thread dependency is allowed
- every header is self-contained and uses `#pragma once`. QRMatrix.h directly includes <array>, <cstddef>, and <stdexcept>. QRCodec.h directly includes <string> and "QRMatrix.h". QRRenderer.h directly includes <string> and "QRMatrix.h". Sources and tests include headers only by basename such as `#include "QRCodec.h"`; `#include "include/QRCodec.h"` and inclusion of any .cpp file are forbidden
- QRMatrix is a fixed value type with public `static constexpr std::size_t SIZE = 21;`, `static constexpr std::size_t FINDER_SIZE = 5;`, constructor QRMatrix(), bool get(std::size_t row,std::size_t col) const, void set(std::size_t row,std::size_t col,bool value), static bool isFinderCell(std::size_t row,std::size_t col), and static bool expectedFinderValue(std::size_t row,std::size_t col). It stores `std::array<std::array<bool, SIZE>, SIZE> modules_{}`; get/set throw std::out_of_range outside 21x21
- the constructor initializes all modules false and then writes three exact 5x5 finder markers at origins (0,0), (0,16), and (16,0). Within each marker the border is true, the inner ring is false, and only local center (2,2) is true. isFinderCell returns true for exactly those 75 cells; expectedFinderValue uses this same definition. There are no separators and no fourth marker
- QRCodec exposes only static QRMatrix encode(const std::string& text), static std::string decode(const QRMatrix& matrix), and static bool detect(const QRMatrix& matrix) noexcept. Data positions are every non-finder cell in row-major order, exactly 366 positions. The wire bits are one unsigned length byte, then every text byte MSB-first, then one checksum byte equal to the sum of text bytes modulo 256, followed by zero bits to capacity. encode rejects text.size()>40 with std::invalid_argument
- decode first compares every finder cell to QRMatrix::expectedFinderValue, then reads non-finder bits row-major. It parses unsigned length N from the first 8 bits, rejects N>40 or insufficient data, reconstructs exactly N bytes MSB-first, validates the following checksum byte against sum(payload)%256, requires every remaining data bit to be false, and returns the exact byte string. Invalid finder/checksum/length/padding throws std::runtime_error. detect returns false on every exception and true only when decode succeeds
- QRRenderer exposes only static std::string render(const QRMatrix&,const std::string& on="##",const std::string& off="  "). It rejects empty markers, emits exactly 21 lines separated by exactly 20 newline characters with no trailing newline, and performs no I/O
- src/Main.cpp encodes literal "CodeWM", decodes it, prints at most one concise line, and returns 0. tests/test_main.cpp directly includes <cassert>, <stdexcept>, <string>, "QRCodec.h", and "QRRenderer.h"; it defines exactly one `int main()` and no framework
- tests/test_main.cpp has exactly three short blocks: (1) encode/decode literal `hello-\u4e16\u754c`, assert detect true and decoded equality; (2) copy with `QRMatrix corrupted = matrix;`, literally call `corrupted.set(0, 0, false);`, assert detect false, and assert decode throws std::runtime_error; (3) assert render has 20 newline characters and assert encoding `std::string(41, 'a')` throws std::invalid_argument. Never set finder [0][0] to true because its valid value is already true
- repeat the exact nine-file list, self-contained includes, fixed marker definition, 366 row-major data positions, byte-length/payload/checksum/zero-padding format, exact public APIs, literal corruption statement, single-main test, and three scopes in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, C++ Build Link Audit, and every affected implementation task
"""
    elif unit["unit_id"] == "p09_qr_code_gen_det_java":
        unit_specific_constraints = """


Project-specific Java deterministic QR-like codec and padding contract:
- use exactly these files and no substitutes, in dependency order: pom.xml, src/main/java/QRMatrix.java, src/main/java/Checksum.java, src/main/java/ZigZag.java, src/main/java/FinderPattern.java, src/main/java/TextEncoder.java, src/main/java/MatrixValidator.java, src/main/java/QRDetector.java, src/main/java/QRCodec.java, src/main/java/QRRenderer.java, src/main/java/Main.java, src/test/java/MainTest.java; every class is in the default package
- pom.xml targets Java 11, declares JUnit Jupiter in test scope, and configures a JUnit-5-capable Maven Surefire plugin; no runtime dependency, network, GUI, input, randomness, clock, filesystem image, or third-party QR library is allowed
- Checksum.sumMod256(byte[] data) sums every supplied byte as unsigned and returns the sum modulo 256. TextEncoder.encodePayload(String text) UTF-8 encodes text, prepends a two-byte unsigned big-endian payload length, and appends exactly one checksum byte computed over ONLY the two length bytes plus UTF-8 payload bytes, never over the checksum slot itself. Both encodePayload and decodePayload must literally obtain that checksum input with `java.util.Arrays.copyOf(frame, frame.length - 1)` and compare the expected checksum to `(frame[frame.length - 1] & 0xFF)`. Calling Checksum.sumMod256(frame) on the complete frame during validation is forbidden because it incorrectly includes the checksum byte
- TextEncoder.decodePayload(byte[] frame) requires the frame length to be exactly 2+L+1, validates the prefix-only checksum before strict UTF-8 decoding, and `TextEncoder.decodePayload(TextEncoder.encodePayload("hello-\u4e16\u754c"))` must round-trip directly even without a matrix
- TextEncoder.bytesToBits(byte[] bytes) emits exactly eight MSB-first bits per byte using the literal assignment `bits[i * 8 + bit] = (bytes[i] & (1 << (7 - bit))) != 0;`. TextEncoder.bitsToBytes(boolean[] bits) MUST accept every non-null bit-array length, including zero and lengths not divisible by eight, and pads the final partial byte with trailing zero bits. It must literally allocate `byte[] result = new byte[(bits.length + 7) / 8];` and set each true bit with `result[i / 8] |= (byte) (1 << (7 - (i % 8)));`. A check, exception, assertion, early return, or truncation based on `bits.length % 8 != 0` is forbidden
- the direct padding fixture is literal: `TextEncoder.bitsToBytes(new boolean[]{true,false,false,false,false,false,false,false,true})` returns a two-byte array whose unsigned values are 128 and 128; MainTest must include this fixture so rejecting or dropping the ninth bit cannot pass
- FinderPattern.reservedMask(size), FinderPattern.place(matrix), FinderPattern.verify(matrix), and ZigZag.traversal(size,reserved) use one identical three-finder reserved-cell definition. QRCodec.encode writes framed payload bits to the traversal prefix and leaves every unused data cell false
- ZigZag.traversal uses one exact finite two-pass row-serpentine algorithm, not an open-ended diagonal state machine: first validate that reserved is exactly size by size, set `int count = 0;`, scan every row and column once and increment count only for `!reserved[row][col]`, then allocate exactly `int[][] result = new int[count][2];`. In a second bounded `for (int row = 0; row < size; row++)` pass, visit columns 0 through size-1 on even rows and size-1 through 0 on odd rows, append `[row,col]` only when the cell is not reserved, and return after exactly count insertions
- ZigZag.traversal MUST NOT allocate `new int[size * size][2]`, MUST NOT terminate on `index < size * size`, and MUST NOT use any while loop or leave zero-coordinate placeholder entries. These forms can never terminate after reserved cells are skipped and previously caused Index 21 out-of-bounds. Both encode and decode use the exact returned `count` coordinates without re-filtering them
- MatrixValidator accepts only odd sizes at least 21. MatrixValidator.capacityBits(size) derives capacity by counting false entries in FinderPattern.reservedMask(size) and may round that count down to a multiple of eight; it must not subtract three pattern areas in a way that double-counts overlaps. QRDetector.readDataBits(QRMatrix matrix) deliberately returns every unreserved traversal bit, whose length need not be divisible by eight; no caller may assume its length is byte-aligned
- QRDetector.extractPayloadBytes first calls readDataBits, then calls TextEncoder.bitsToBytes on that complete possibly-non-byte-aligned array. It reads unsigned L from the first two resulting bytes, computes exactly `int frameLength = 2 + length + 1;`, rejects insufficient bytes, then literally uses `byte[] frame = java.util.Arrays.copyOf(bytes, frameLength);`, validates that exact frame with TextEncoder.decodePayload(frame), and returns frame. It ignores only the zero-filled unused matrix suffix by truncating according to L; it must never pass all capacity bytes to an exact-length decoder
- QRCodec.encode(String,int), encode(String), and decode(QRMatrix) use that single framing path. Auto-size must literally begin with `int size = 21;`, then add two while capacity is insufficient; QRCodec must never read a MatrixValidator.MIN_SIZE field or any other visibility-sensitive constant. QRRenderer.render produces exactly one deterministic line per matrix row and performs no I/O
- Because every project class is in Java's unnamed/default package, MainTest imports ONLY `org.junit.jupiter.api.Test` and static members from `org.junit.jupiter.api.Assertions`. It directly refers to QRCodec, QRMatrix, TextEncoder, QRRenderer, and Main without importing them. Lines such as `import QRCodec;`, `import QRMatrix;`, or imports of any other default-package project class are invalid Java and strictly forbidden
- Main.main encodes, renders, and decodes one fixed short string, prints at most one concise result, and returns normally. MainTest contains exactly three concise JUnit Jupiter tests: (1) Main.main returns normally; (2) the exact nine-bit padding fixture above, direct `TextEncoder.decodePayload(TextEncoder.encodePayload("hello-\u4e16\u754c"))`, plus `codec.decode(codec.encode("hello-\u4e16\u754c"))` all round-trip and rendering has one line per row; (3) corrupting a copied finder cell `[0][0]` makes decode throw IllegalArgumentException. Tests never locate an arbitrary payload bit or assume unused traversal length is divisible by eight
- repeat the exact file list, Java 11 build, prefix-only checksum calculation, direct payload round-trip, exact bytesToBits inverse, default-package import ban, literal size-21 auto-size start, literal ceil-allocation and bit-setting statements, ban on modulo rejection, complete-bit-read rule, length-determined Arrays.copyOf truncation, exact nine-bit fixture, and three-test scopes in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, and every affected implementation task; vague statements such as "pad partial bytes" are insufficient
"""
    elif unit["unit_id"] == "p09_qr_code_gen_det_python":
        unit_specific_constraints = """


Project-specific Python deterministic QR-like codec contract:
- use exactly these files and no substitutes: requirements.txt, qr_code/payload.py, qr_code/matrix.py, qr_code/codec.py, qr_code/render.py, qr_code/__init__.py, Main.py, tests/test_main.py
- use Python's built-in bytes type directly in annotations; `from typing import bytes` and every other attempt to import bytes from typing are forbidden. Prefer built-in list/dict annotations and import no typing name unless it actually exists in Python 3.10
- payload.py imports no project module and defines encode_text(text:str)->bytes using UTF-8, pack_payload(data:bytes)->list[int], and unpack_payload(bits:list[int])->bytes. pack_payload accepts at most 40 bytes and returns exactly an 8-bit unsigned byte length, then every payload byte most-significant-bit first, then an 8-bit checksum sum(data)%256; unpack_payload validates every supplied bit, reads the first 8 bits as byte length N, requires N<=40 and at least 16+8*N supplied bits, reads data and checksum only from that prefix, requires every remaining trailing matrix-padding bit to be zero, ignores that zero padding, and raises ValueError on truncation, nonzero padding, or checksum corruption
- matrix.py imports no project module and uses exactly SIZE=21 and FINDER_SIZE=5. A finder marker is the exact 5x5 pattern whose border is 1, inner ring is 0, and center is 1; place_finder_patterns(matrix:list[list[int]])->None places it at top-left (0,0), top-right (0,16), and bottom-left (16,0). data_positions()->list[tuple[int,int]] returns all non-finder cells in deterministic row-major order
- matrix.py also defines build_matrix(bits:list[int])->list[list[int]], extract_bits(matrix:list[list[int]])->list[int], and validate_matrix(matrix:object)->bool. build_matrix rejects non-bits or excess capacity, starts from a 21x21 zero matrix, places all three finder markers, then writes bits through data_positions; extract_bits requires validate_matrix and reads those positions; validate_matrix returns false rather than raising for non-21x21/ragged/non-binary matrices or an incorrect finder marker
- codec.py imports only from .payload and .matrix and defines generate(text:str)->list[list[int]], decode(matrix:list[list[int]])->str, and detect(matrix:object)->bool. generate returns build_matrix(pack_payload(encode_text(text))); decode uses exactly `unpack_payload(extract_bits(matrix)).decode("utf-8", errors="strict")` after matrix validation, passes extracted bits directly to unpack_payload without first grouping or converting the 366-bit list into bytes, and raises ValueError for every invalid matrix or payload; detect returns true only when decode succeeds and catches validation, checksum, and UTF-8 errors
- render.py imports only validate_matrix from .matrix and defines render(matrix:list[list[int]],on:str="##",off:str="  ")->str; it rejects an invalid matrix or empty marker strings and returns exactly 21 newline-joined rows without printing
- qr_code/__init__.py explicitly re-exports encode_text, pack_payload, unpack_payload, place_finder_patterns, data_positions, build_matrix, extract_bits, validate_matrix, generate, decode, detect, and render; no wildcard imports and no alternate validate alias
- Main.py uses `from qr_code import generate, decode, detect, render`, exposes run_demo()->dict that generates the literal text "CodeWM" and returns exactly text, decoded, detected, size, rendered_lines; decoded is "CodeWM", detected is True, size is 21, and rendered_lines is 21. main() prints at most one concise result under the __name__ guard
- tests/test_main.py contains exactly three concise pytest tests with absolute imports: (1) run_demo has the exact values above; (2) generate("hello-\u4e16\u754c") returns a 21x21 matrix for which validate_matrix and detect are true, decode returns exactly "hello-\u4e16\u754c", `unpack_payload(extract_bits(matrix)).decode("utf-8")` also returns exactly "hello-\u4e16\u754c" despite the extracted trailing zero padding, and render has 21 lines; (3) copy the matrix by `[row[:] for row in matrix]`, flip corrupted[0][0], then validate_matrix and detect are false and decode raises ValueError, while validate_matrix([[0,1],[1,0]]) is false
- tests and implementation use only the canonical function names; version arguments, variable matrix sizes, third-party QR libraries, random masks, timestamps, filesystem images, network access, and GUI dependencies are forbidden
- repeat the exact file list, built-in-bytes rule, 21x21/5x5 constants, payload length/checksum/zero-padding wire format, direct extract_bits-to-unpack_payload decoding rule, function signatures, three-test limit, and all literal fixtures in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, and every affected implementation task
"""
    elif unit["unit_id"] == "p10_crud_system_cpp":
        unit_specific_constraints = """


Project-specific C++17 deterministic in-memory CRUD contract:
- replace the over-split Query/Audit/interface architecture with exactly these files in dependency order: CMakeLists.txt, include/Record.h, src/Record.cpp, include/ManualClock.h, src/ManualClock.cpp, include/Repository.h, src/Repository.cpp, include/CrudService.h, src/CrudService.cpp, src/Main.cpp, tests/test_main.cpp. Do not create Id, Clock, Query, Audit, MemoryRepository, abstract interfaces, namespaces, or additional source/test files
- CMakeLists.txt sets C++17 with extensions off, builds crud_core from Record.cpp, ManualClock.cpp, Repository.cpp, and CrudService.cpp, publishes `${CMAKE_CURRENT_SOURCE_DIR}/include`, builds crud_app and crud_tests, links both to crud_core, calls enable_testing(), and registers crud_tests. No external package, FetchContent, network, filesystem, database, GUI, threads, randomness, or wall clock is allowed
- every header is self-contained and uses `#pragma once`: Record.h directly includes <cstdint> and <string>; ManualClock.h directly includes <cstdint>; Repository.h directly includes <map>, <optional>, <string>, <vector>, and "Record.h"; CrudService.h directly includes <optional>, <string>, <vector>, "ManualClock.h", "Record.h", and "Repository.h". Every source/test includes headers by basename, never `include/...`, and no source relies on a transitive standard-library include
- Record is exactly `struct Record` with public fields `std::string id`, name, email; `std::uint64_t revision`, updated_at; constructor Record(std::string id,std::string name,std::string email,std::uint64_t revision,std::uint64_t updated_at); and value-based `bool operator==(const Record&) const`. There is no default constructor and no field spelling variant such as createdAt or updatedAt
- ManualClock has explicit ManualClock(std::uint64_t initial), std::uint64_t now() const noexcept, and void advance(std::uint64_t delta) noexcept. It stores one counter and never reads the system clock
- Repository is one concrete in-memory class backed by `std::map<std::string, Record> records_`. It exposes bool insert(const Record&), std::optional<Record> find(const std::string&) const, bool replace(const Record&), bool erase(const std::string&), and std::vector<Record> list() const. insert returns false for duplicate id; replace returns false when absent; list follows deterministic map key order. Repository.h directly includes Record.h, so Record is visible in every declaration
- CrudService owns references `Repository& repository_` and `ManualClock& clock_`, with constructor CrudService(Repository&,ManualClock&). It exposes Record create(const std::string& id,const std::string& name,const std::string& email), std::optional<Record> get(const std::string& id) const, Record update(const std::string& id,const std::string& name,const std::string& email), bool remove(const std::string& id), and std::vector<Record> list() const. create/update reject blank id/name and email lacking one non-edge @ with std::invalid_argument; duplicate create and absent update throw std::runtime_error. create stores revision=1 and updated_at=clock.now(); update preserves id, increments revision by one, and takes a fresh clock.now()
- src/Main.cpp constructs Repository, ManualClock(100), CrudService, creates id "1", prints at most one concise value, and returns 0. tests/test_main.cpp directly includes <cassert>, <stdexcept>, <string>, "CrudService.h" and defines exactly one self-contained int main(), no test framework
- tests/test_main.cpp contains exactly three short blocks: (1) Repository repo; ManualClock clock(100); CrudService service(repo,clock); create("1","Alice","alice@example.com") has revision1/updated_at100, get returns it, advance(5), update to Alice Smith has revision2/updated_at105, remove returns true and get is empty; (2) blank name, malformed email, and duplicate id each throw the specified exception; (3) create id "b" then "a" and assert list size2 with ids "a" then "b". Each block uses fresh Repository/ManualClock/CrudService objects
- constructor declarations appear only in headers and definitions only in matching .cpp files; never write both `ManualClock(...) = default` in the header and an out-of-line definition. Repeat the exact eleven-file list, direct includes, field spellings, signatures, exceptions, deterministic fixtures, single-main test, and three scopes in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, C++ Build Link Audit, and every affected implementation task
"""
    elif unit["unit_id"] == "p10_crud_system_python":
        unit_specific_constraints = """


Project-specific Python 3.10 CRUD pagination contract:
- preserve exactly these files in dependency order: requirements.txt, crud_system/errors.py, crud_system/types.py, crud_system/clock.py, crud_system/validation.py, crud_system/repository.py, crud_system/search.py, crud_system/audit.py, crud_system/service.py, crud_system/__init__.py, Main.py, tests/test_main.py. Do not add or rename modules
- crud_system/types.py is the sole owner of Item, AuditEvent, and Page. Page is an ordinary dataclass declared as `class Page:` with fields items:list[Item], total:int, limit:int, offset:int. Page is deliberately not generic: TypeVar, Generic, `class Page(Generic[T])`, `Page[Item]`, and every other Page subscription are forbidden
- crud_system/search.py directly imports Item and Page from .types. Its pagination signature is exactly `paginate(items:list[Item],limit:int|None=None,offset:int=0)->Page`; it returns `Page(items=selected,total=len(items),limit=effective_limit,offset=offset)`, rejects a negative offset or negative non-None limit with PaginationError, and never annotates a return as Page[Item]
- all public annotations are valid when modules are imported under Python 3.10. A class used with square-bracket generic syntax must actually inherit from typing.Generic, but this repository must use the simpler non-generic Page contract above. Tests must import the complete package successfully before running any assertion
- errors.py solely defines ValidationError, DuplicateNameError, NotFoundError, and PaginationError. repository.py directly contains `from .errors import DuplicateNameError, NotFoundError`; search.py directly imports PaginationError. Every referenced exception is directly imported in the module that raises it, and no module relies on re-export side effects
- FixedClock(base:float=100.0,step:float=10.0) returns the current value from now() and then advances by step. AuditTrail() takes no clock and never calls now(); its log method receives an explicit timestamp. Service(Repository,AuditTrail,FixedClock) is the sole clock consumer and each create/update/delete operation calls clock.now() exactly once, stores that value in the entity change, and passes the identical value to AuditTrail. A single operation must never advance the clock twice
- preserve deterministic validation, duplicate-name conflict, search/filter/sort, and CRUD behavior. Main.py constructs AuditTrail() without a clock, remains a bounded non-interactive demo, and requirements.txt lists pytest only
- tests/test_main.py contains exactly three concise pytest tests: (1) basic CRUD uses FixedClock(100.0,10.0), creates at 100.0 and updates at 110.0, with entity and audit timestamps identical for each operation; (2) duplicate-name creation raises DuplicateNameError and missing access raises NotFoundError; (3) creation of Alpha, Beta, Gamma yields pagination limit2/offset1 names Beta and Gamma and audit timestamps exactly [100.0,110.0,120.0]. Tests use only canonical exports from crud_system and do not inspect private members
- repeat the exact file list, non-generic Page declaration, exact paginate signature, `Page[Item]` prohibition, direct exception imports, single-clock-call ownership, AuditTrail() constructor, the exact three fixtures, Python-3.10 importability requirement, and exactly-three-test rule in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, and every affected implementation task
"""
    elif unit["unit_id"] == "p10_crud_system_java":
        unit_specific_constraints = """


Project-specific Java 11 entity and compilation contract:
- use exactly these files and no substitutes, in dependency order: pom.xml, src/main/java/User.java, src/main/java/AuditEvent.java, src/main/java/UserValidator.java, src/main/java/SearchService.java, src/main/java/AuditLogService.java, src/main/java/UserRepository.java, src/main/java/InMemoryUserRepository.java, src/main/java/Main.java, src/test/java/MainTest.java
- the phrase "typed records" means typed stored domain objects, not the Java record language feature. Java `record` declarations are forbidden because the evaluator compiles with Java 11; sealed classes, pattern matching, text blocks, and every other post-Java-11 syntax are also forbidden
- User.java defines an ordinary `public final class User`, never `public record User`, with private final String id, name, and email, a constructor User(String id,String name,String email) that stores its three arguments unchanged (including null or blank values) and never validates them, getters getId/getName/getEmail, and value-based equals/hashCode/toString. This deliberately makes invalid candidate values constructible so the separate UserValidator can be tested
- AuditEvent.java defines an ordinary `public final class AuditEvent`, never `public record AuditEvent`, with private final long timestamp plus private final String action and userId, a validating constructor, getters getTimestamp/getAction/getUserId, and value-based equals/hashCode/toString; deterministic tests pass explicit fixed timestamps and never assert the wall clock
- UserValidator is stateless and `boolean isValid(User user)` returns false, never throws, for null users or a null/blank id, name, or email; it returns true otherwise. InMemoryUserRepository.save calls this validator and throws IllegalArgumentException for invalid input, while the User constructor itself never validates
- SearchService is stateless. `List<User> search(List<User> users,String query)` returns a new empty list for a null users list, a defensive copy for a null/blank query, and otherwise returns non-null users whose lower-cased name has a whitespace-delimited token exactly equal to the trimmed lower-cased query. It searches names only, preserves input order, and never mutates the input. The canonical fixture Alice Smith/Bob Jones searched with "smith" returns only Alice Smith
- AuditLogService is an independent explicit log: only `log(AuditEvent event)` changes it. It has no static/global state, and InMemoryUserRepository has no AuditLogService field and never logs implicitly. Tests must explicitly call auditLogService.log for each event before asserting getAllEvents
- UserRepository.java must literally begin with `import java.util.List;` before its public interface declaration, because it returns `List<User>` and default-package classes do not provide java.util imports. Every other Java file that spells `List`, `ArrayList`, `Map`, `HashMap`, or `Objects` must likewise contain its own direct matching java.util import and must never rely on a transitive import. UserRepository declares findById, findAll, save, and deleteById. InMemoryUserRepository.save is deterministic upsert by id: first save creates, a later save with the same id replaces the value. findById returns null when absent; findAll and AuditLogService.getAllEvents return defensive lists
- Main.java is a thin non-interactive demo and must contain no collection type declaration: no `List`, `ArrayList`, `Map`, or collection result variable. It may construct SearchService and invoke `searchService.search(repository.findAll(), "alice");` as a standalone expression without storing the returned list; consequently Main needs no java.util import. MainTest.java uses JUnit Jupiter and contains exactly three `@Test` methods, no more: (1) runtime plus ordinary User/AuditEvent value-object getters/equality with timestamp 1640995200000L; (2) validation plus search, constructing `new User("", null, "")` and asserting validator false, then searching `[new User("1","Alice Smith","alice@example.com"), new User("2","Bob Jones","bob@example.com")]` for `"smith"` and asserting only Alice; (3) CRUD plus explicit audit, upserting id 1, deleting it, explicitly logging fixed CREATE_USER and DELETE_USER events into the same local AuditLogService instance, and asserting exactly those two events. Tests never expect repository operations to log implicitly and never use record component syntax or reflection
- Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, and every affected implementation task must repeat the direct `import java.util.List;` requirement, Main.java no-collection-declaration rule and standalone search call, non-validating User constructor/separate-validator rule, exact name-token search rule and Alice/Bob fixture, explicit non-coupled audit rule, upsert rule, exactly-three-test rule, and fixed fixtures above, as well as `public final class User`, `public final class AuditEvent`, and "Java record syntax is forbidden under Java 11" verbatim; a Logic Analysis description saying "defines User record" or "defines AuditEvent record" invalidates the architecture
"""
    elif unit["unit_id"] == "p11_custom_press_releases_python":
        unit_specific_constraints = """


Project-specific Python press-release lifecycle without clock/dataclass traps:
- use exactly these files and no substitutes, in dependency order: requirements.txt, press_releases/errors.py, press_releases/types.py, press_releases/template.py, press_releases/validation.py, press_releases/press_release.py, press_releases/search.py, press_releases/__init__.py, Main.py, tests/test_main.py. Do not create clock.py, history.py, lifecycle.py, rendering.py, repository.py, service.py, or any additional source/test file
- no module imports datetime, time, random, uuid, pathlib, os, threading, or a clock abstraction. Version history is deterministic and uses monotonically increasing integer version numbers only; tests never assert a wall-clock timestamp
- errors.py solely defines DomainError(ValueError) and InvalidTransitionError(DomainError). types.py solely defines enum State with DRAFT, REVIEW, PUBLISHED; frozen dataclass Contact(name:str,email:str); and frozen dataclass VersionEntry(number:int,rendered_text:str). These frozen value objects use only the generated dataclass initializer and define no custom __init__
- template.py defines frozen dataclass Template(name:str,content:str) with render(fields:dict[str,str]|None=None)->str and no custom __init__. Its implementation is literal and finite: set `values = {} if fields is None else fields`, set `result = self.content`, then `for key in sorted(values):` execute `result = result.replace("{{" + key + "}}", values[key])`, and return result. It leaves missing placeholders unchanged. Parsing placeholders with result.split("{{"), slicing parts such as part[2:-2], regular expressions, or an open-ended scanning loop is forbidden
- validation.py defines validate_headline(str)->bool, validate_body(str)->bool, and validate_contact(Contact)->bool. They return false rather than throwing for invalid values; contact requires nonblank name and an email containing one @ with nonempty sides
- press_release.py defines an ordinary mutable `class PressRelease:` and MUST NOT decorate it with `@dataclass`, `@dataclass(frozen=True)`, attrs, NamedTuple, or another frozen mechanism. Its constructor PressRelease(id:str,headline:str,body:str,contact:Contact,template:Template,custom_fields:dict[str,str]|None=None) assigns normal mutable attributes and starts State.DRAFT with empty insertion-ordered tags and empty version history. The constructor deliberately does not validate and never raises merely because headline/body/contact are invalid, so invalid candidate values remain constructible for validate tests
- PressRelease exposes properties id/headline/body/contact/state; validate()->bool; submit_for_review()->None; publish()->None; add_tag(tag:str)->None; tags()->list[str]; render_plain_text()->str; version_history()->list[VersionEntry]. validate returns false and never throws for invalid fields. submit_for_review on invalid content raises DomainError, otherwise requires DRAFT then sets REVIEW; publish requires REVIEW then sets PUBLISHED and appends exactly VersionEntry(1,render_plain_text()) on the first publication; invalid state transitions raise InvalidTransitionError. add_tag trims, rejects blank with DomainError, and preserves unique insertion order. Returned lists are defensive copies
- render_plain_text combines custom_fields with headline/body/contact/contact_name/contact_email and calls Template.render. search.py defines search_by_tag(releases:list[PressRelease],tag:str)->list[PressRelease] and search_text(releases:list[PressRelease],query:str)->list[PressRelease], preserves order, ignores None releases, uses exact normalized tag matching and case-insensitive headline/body containment, and never mutates inputs
- __init__.py re-exports only real canonical names: DomainError, InvalidTransitionError, State, Contact, VersionEntry, Template, the three validators, PressRelease, search_by_tag, and search_text. It MUST NOT export, import, or mention run_demo. Main.py uses absolute imports from press_releases, exposes run_demo()->dict[str,object], performs a fixed non-interactive lifecycle demonstration, and main prints at most one concise line only under the __name__ guard
- requirements.txt contains only a Python-3.10-compatible pytest requirement. tests/test_main.py must contain the separate literal line `from Main import run_demo`; it imports all other symbols from press_releases and MUST NEVER put run_demo in a `from press_releases import ...` statement. It uses exactly three concise tests: (1) run_demo returns a dict and reaches PUBLISHED; (2) Template("basic","{{headline}}|{{body}}|{{contact_email}}") plus Contact("Alice","a@b.com") renders exactly `Hello|Body|a@b.com`, validates, transitions DRAFT to REVIEW to PUBLISHED, and yields exactly one VersionEntry numbered 1 with the same text; (3) constructs a candidate with blank headline and Contact("","invalid"), asserts candidate.validate() is False without expecting its constructor to throw, asserts candidate.submit_for_review() raises DomainError, then constructs a separate valid release with headline "Hello" that remains DRAFT and immediately executes `with pytest.raises(InvalidTransitionError): valid_draft.publish()` before any submit_for_review call on that object; afterward it may add media then news tags to valid_draft, verifies their insertion order, search_by_tag media, and case-insensitive search_text hello. The third test MUST NOT call valid_draft.submit_for_review() before its expected failing publish
- repeat the exact 10-file list, explicit clock/datetime prohibition, literal sorted-field replacement loop and forbidden split/slice parser, ordinary non-dataclass PressRelease requirement, non-validating constructor/false-returning validate rule, generated-only initializer rule for frozen value objects, integer version history, canonical APIs, the separate literal `from Main import run_demo` test import and forbidden press_releases run_demo import, the exact DRAFT publish sequence, exact fixtures, and three-test limit in Full API specification, Logic Analysis, Test Include Plan, Test Scope Plan, Shared Knowledge, and every affected implementation task
"""
    elif unit["unit_id"] == "p11_custom_press_releases_java":
        unit_specific_constraints = """


Project-specific Java 11 press-release type-ownership and deterministic-test contract:
- use exactly these files and no substitutes, in dependency order: pom.xml, src/main/java/ReleaseState.java, src/main/java/Version.java, src/main/java/Template.java, src/main/java/Validator.java, src/main/java/PressRelease.java, src/main/java/TaggingSystem.java, src/main/java/RenderService.java, src/main/java/Main.java, src/test/java/MainTest.java
- ReleaseState.java is the sole definition site for `public enum ReleaseState { DRAFT, REVIEW, PUBLISHED }`. Version.java is the sole definition site for ordinary Java 11 `public final class Version` with private final int number and private final String renderedText, constructor Version(int number,String renderedText), getters getNumber/getRenderedText, and value-based equals/hashCode/toString. ReleaseState and Version must never be omitted, nested in another class, or referenced without these definitions; Java record syntax and post-Java-11 syntax are forbidden
- Template.java defines `public final class Template`, constructor Template(String name,String content), getters getName/getContent, and `String applyCustomFields(Map<String,String> fields)`. Placeholders have literal form `{{key}}`; supplied keys are replaced by their values, missing placeholders remain unchanged, a null map acts as an empty map, and the Template is immutable
- Validator.java defines a stateless `public final class Validator` with exactly the static methods validateHeadline(String), validateBody(String), and validateContact(String). The first two accept non-null non-blank text; validateContact additionally requires one `@` with nonempty text on both sides. Validation returns false and never throws for null/invalid text
- PressRelease.java defines ordinary `public final class PressRelease` with constructor PressRelease(String id,String headline,String body,String contact,Template template,Map<String,String> customFields). It exposes getId/getHeadline/getBody/getContact/getState, validate(), submitForReview(), publish(), addTag(String), getTags(), renderPlainText(), and getVersionHistory(). It starts DRAFT; submitForReview requires validate()==true and DRAFT then changes to REVIEW; publish requires REVIEW then changes to PUBLISHED and appends exactly one `new Version(1, renderPlainText())` for the first publication. Collections are insertion-ordered defensive copies, invalid transitions throw IllegalStateException, and no clock, timestamp, randomness, filesystem, or network is used
- PressRelease.renderPlainText builds a new field map containing headline, body, and contact plus the constructor customFields and passes it to Template.applyCustomFields. TaggingSystem is stateless and defines `static List<PressRelease> searchByTag(List<PressRelease> releases,String tag)`, preserving input order and returning releases whose getTags contains the exact trimmed tag. RenderService is stateless and defines `static String toPlainText(PressRelease release)` delegating to release.renderPlainText; neither service owns ReleaseState or Version
- Main.java is a thin non-interactive Java 11 demo. MainTest.java uses JUnit Jupiter and contains exactly three `@Test` methods: (1) Main.main(new String[0]) returns normally; (2) Template("basic","{{headline}}|{{body}}|{{contact}}") substitution yields `Hello|Body|a@b.com` and Validator accepts those three values but rejects a blank headline and contact "invalid"; (3) construct release id "r1" with those values, assert DRAFT, submitForReview then assert REVIEW, add tag "media", publish then assert PUBLISHED, render exact `Hello|Body|a@b.com`, assert version history size 1 with Version number 1 and the same rendered text, and assert TaggingSystem.searchByTag(Arrays.asList(release),"media") returns only that release
- Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, and every affected implementation task must repeat the exact 10-file list, sole ReleaseState/Version ownership, all canonical signatures, lifecycle rules, literal template/validation/lifecycle fixtures, exactly-three-test limit, and Java 11 restriction. Any architecture that references ReleaseState or Version without their two files is invalid
"""
    elif unit["unit_id"] == "p12_video_player_java":
        unit_specific_constraints = """


Project-specific Java 11 deterministic video-player state contract:
- use exactly these default-package files and no substitutes, in dependency order: pom.xml, src/main/java/MediaItem.java, src/main/java/Playlist.java, src/main/java/PlayerState.java, src/main/java/VolumeControl.java, src/main/java/DeterministicClock.java, src/main/java/PlayerSnapshot.java, src/main/java/PlaybackController.java, src/main/java/Main.java, src/test/java/MainTest.java. Do not add package declarations, interfaces, clocks, exception files, or additional source/test files
- MediaItem is a public final class with final String id/title and long durationMillis; constructor requires nonblank id/title and durationMillis>0; getters expose all three. Playlist is a public final class backed by ArrayList<MediaItem>; add rejects null; size/getAt/removeAt use ordinary list semantics; hasNext(index), hasPrevious(index), nextIndex(index), and previousIndex(index) are bounds-safe. For nonempty lists nextIndex clamps into [0,size-1] and previousIndex clamps into [0,size-1]; for empty lists both return -1
- PlayerState is a public final class owning nested enum PlaybackStatus { STOPPED, PLAYING, PAUSED }. Its zero-argument constructor MUST initialize `currentIndex = 0`, `positionMillis = 0`, and `status = PlaybackStatus.STOPPED`; initializing currentIndex to -1 is forbidden. It provides get/setCurrentIndex, get/setPositionMillis (reject negative), get/setStatus (reject null), and resetPosition
- VolumeControl is a public final class initialized with volume=100, lastNonMuted=100, muted=false. setVolume validates [0,100], always assigns both `this.volume = volume` and `this.lastNonMuted = volume`, including while muted. mute sets muted=true without changing those fields; unmute sets muted=false and assigns volume=lastNonMuted; getEffectiveVolume returns muted?0:volume. A setVolume call while muted therefore changes the value restored by unmute; preserving the pre-mute value instead is forbidden
- DeterministicClock is a public final class with currentTimeMillis=0, getCurrentTimeMillis(), and advance(long deltaMillis) rejecting negative delta and adding nonnegative delta. No wall clock, Thread.sleep, timer, randomness, GUI, filesystem, or network is used
- PlayerSnapshot is an immutable public final value with index, title, positionMillis, durationMillis, PlayerState.PlaybackStatus status, volume, and muted; it has a constructor, getters, and static from(Playlist,PlayerState,VolumeControl). For an empty/invalid index it returns a safe empty title/duration snapshot; for a valid index it reads that MediaItem
- PlaybackController is a public final class constructed from nonnull Playlist, VolumeControl, DeterministicClock; it creates a PlayerState (therefore index 0) and stores lastTick=clock.getCurrentTimeMillis(). play rejects an empty playlist, accepts index 0 for a nonempty playlist, resets position to zero only if already at duration, and sets PLAYING. pause sets PAUSED. stop sets STOPPED and position zero. seek clamps to [0,current duration]. next/previous use Playlist bounds helpers, reset position only when index actually changes, and remain at last/first index at bounds. onClockAdvanced computes nonnegative delta from lastTick, advances only while PLAYING, clamps at duration and changes to STOPPED while keeping position exactly duration. getSnapshot/getState/getPlaylist/getVolumeControl expose the canonical objects
- Main.java constructs a small in-memory playlist and deterministic clock, runs a bounded demo, and exits without input or loops. pom.xml compiles source/target 11 and uses only JUnit Jupiter test dependency with Surefire
- MainTest.java contains exactly three JUnit Jupiter @Test methods. Test 1: one MediaItem duration 5000, new controller, play, clock.advance(5000), onClockAdvanced; snapshot is index0, position5000, duration5000, STOPPED. Test 2: two items durations 3000/4000; initial play succeeds at index0; seek(5000) clamps to3000; next makes index1/position0, a second next remains index1; previous makes index0, a second previous remains index0. Test 3: setVolume(70), mute gives effective0, setVolume(30) while muted makes getVolume30/effective0, unmute makes getVolume30/effective30
- repeat the exact 10-file list, default-package rule, PlayerState index-zero literal initialization and forbidden -1, VolumeControl assignment while muted, deterministic clock, exact controller semantics, exact three tests and fixtures, Java 11 requirement, and no external effects in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, and every affected implementation task
"""
    elif unit["unit_id"] == "p12_video_player_cpp":
        unit_specific_constraints = """


Project-specific C++ fixed-width integer compilation contract:
- use exactly these files and no substitutes, in dependency order: CMakeLists.txt, include/Time/IClock.h, include/Time/ManualClock.h, include/Time/MonotonicClock.h, include/Media/MediaMetadata.h, include/Playlist/Playlist.h, include/Player/PlaybackState.h, include/Player/Player.h, include/Runtime/App.h, src/Time/ManualClock.cpp, src/Time/MonotonicClock.cpp, src/Media/MediaMetadata.cpp, src/Playlist/Playlist.cpp, src/Player/Player.cpp, src/Runtime/App.cpp, src/Main.cpp, tests/test_main.cpp
- every header that names a signed 64-bit integer must directly contain `#include <cstdint>` and must spell the type `std::int64_t`; bare `int64_t` is forbidden everywhere. In particular include/Time/IClock.h begins its standard-library includes with `#include <cstdint>` before namespace Time and declares `virtual std::int64_t now_ms() const noexcept = 0;`
- ManualClock and MonotonicClock override exactly `std::int64_t now_ms() const noexcept`; all ManualClock start/delta/current values, MediaMetadata duration values, and Player position/duration/last-time values and parameters use `std::int64_t` consistently in declarations and definitions. Do not mix const/non-const or noexcept/throwing forms across base, derived, header, and source signatures
- tests/test_main.cpp is a self-contained zero-third-party test executable with exactly one `int main()` and ordinary standard-library checks; GoogleTest, Catch2, Boost.Test, doctest, and every other test dependency are forbidden. CMakeLists.txt directly uses `add_executable(video_player_tests tests/test_main.cpp)`, links the project core library, calls `enable_testing()` and `add_test(NAME video_player_tests COMMAND video_player_tests)`, and never uses find_package, FetchContent, ExternalProject, GTest, gtest, or network downloads
- src/Main.cpp contains only a minimal `int main()` that returns `Runtime::App().run_demo()` (or equivalently constructs App then returns run_demo). It never streams or prints PlaybackState or another enum, and contains no interactive or long-running loop
- Full API specification, Logic Analysis, Shared Knowledge, test/build plan, and every affected header/source task must repeat the direct `<cstdint>` include rule, `std::int64_t` spelling, exact IClock signature, consistent override rule, zero-third-party self-contained test-main rule, exact CMake test target, and minimal runtime entry. Relying on transitive standard-library includes is forbidden
"""
    elif unit["unit_id"] == "p13_video_downloader_cpp":
        unit_specific_constraints = """


Project-specific C++17 downloader contract with deliberately small boundary interfaces:
- use exactly these files and no substitutes, in dependency order: CMakeLists.txt, include/DownloadTypes.h, include/Url.h, src/Url.cpp, include/SafeNamer.h, src/SafeNamer.cpp, include/Transfer.h, src/Transfer.cpp, include/DownloadQueue.h, src/DownloadQueue.cpp, src/Main.cpp, tests/test_main.cpp. Do not create Format.h, TransferAdapter.h, FakeTransfer.h, ExistingFiles.h, InMemoryExistingFiles.h, or any other source/header/test file
- DownloadTypes.h is self-contained and directly includes <cstddef>, <cstdint>, and <string>. It solely defines global enum class Format { MP4, WEBM, AUDIO }, enum class DownloadState { QUEUED, DOWNLOADING, COMPLETED, CANCELED, FAILED }, struct Progress { std::size_t bytes; std::size_t total; }, struct DownloadItem { std::uint64_t id; std::string url; Format format; std::string filename; DownloadState state; Progress progress; std::string error; }, and struct EnqueueResult { bool ok; std::uint64_t id; std::string filename; std::string error; }. No type in this header depends on another project header, so Format is always defined before DownloadItem
- Url.h directly includes <string> and declares bool is_valid_url(const std::string&), bool parse_format(const std::string&, Format&), and std::string extension_for(Format); it directly includes "DownloadTypes.h" because it names Format. Url.cpp directly includes "Url.h" and <algorithm>/<cctype> as used. URL validation rejects whitespace anywhere, finds a literal :// separator, requires its scheme to be exactly http or https, sets host_begin to separator+3, finds the next slash from host_begin (or uses url.size), and requires host_end>host_begin; a path is NOT required. Therefore both `https://` and `http:///path` are invalid, while BOTH `https://example.com` and `https://example.com/clip` are valid. Treating a host-only URL as invalid is forbidden. Format parsing accepts case-insensitive mp4, webm, audio; extensions are .mp4, .webm, .mp3
- SafeNamer.h directly includes <string>, <unordered_set>, <vector>. It fully declares class IExistingFiles with virtual destructor and pure virtual bool exists(const std::string&) const, then class InMemoryExistingFiles final with a private unordered_set<string>, an explicit zero-argument `InMemoryExistingFiles() = default;`, a separate `explicit InMemoryExistingFiles(const std::vector<std::string>& initial);` with NO default argument, exists override, and add. It also declares sanitize_base and unique_name(base, extension, files, reserved). `InMemoryExistingFiles files({});` is forbidden because braces are ambiguous with copy/move construction; empty instances MUST be spelled exactly `InMemoryExistingFiles files;`. SafeNamer.cpp directly includes "SafeNamer.h", <algorithm>, <cctype>, and <utility> before using std::move. It never calls a method through an incomplete forward-declared type. sanitize_base keeps alphanumeric, dash, underscore, converts other runs to one underscore, trims edge underscores, and falls back to "download"; unique_name returns base+extension or base_2+extension, base_3+extension, etc. while either files.exists or reserved contains the candidate
- Transfer.h directly includes <cstddef> and <string>. It fully declares class ITransferAdapter with virtual destructor and pure virtual std::size_t total_bytes(const std::string& url) const, and class FakeTransferAdapter final whose explicit constructor takes std::size_t total_bytes=12 and whose override returns that fixed value for every URL. Transfer.cpp directly includes "Transfer.h" and validates the constructor total is positive. There is no TransferSession and no bytesTransferred accessor; progress mutation belongs solely to DownloadQueue
- DownloadQueue.h directly includes <cstddef>, <cstdint>, <string>, <unordered_set>, <vector>, plus "DownloadTypes.h", "SafeNamer.h", and "Transfer.h". It defines class DownloadQueue holding ITransferAdapter&, const IExistingFiles&, vector<DownloadItem>, unordered_set<string> reserved_names, next_id starting at 1, and chunk_size. Public API is exact: DownloadQueue(ITransferAdapter&,const IExistingFiles&,std::size_t chunk_size=4); EnqueueResult enqueue(const std::string& url,const std::string& format_text,const std::string& desired_base); bool cancel(std::uint64_t); const DownloadItem* get(std::uint64_t) const; std::vector<DownloadItem> list() const; void tick(). DownloadQueue.cpp MUST directly include both "DownloadQueue.h" and "Url.h" before calling is_valid_url, parse_format, or extension_for, then directly include <algorithm> and <stdexcept>; relying on an undeclared URL function or a transitive include is forbidden
- enqueue rejects invalid URL/format by returning ok=false without adding an item; otherwise reserves a safe unique filename and appends a QUEUED item with progress {0, adapter.total_bytes(url)}. tick deterministically processes only the first QUEUED or DOWNLOADING item: transitions QUEUED to DOWNLOADING, then increments item.progress.bytes directly by min(chunk_size, total-bytes), and marks COMPLETED when bytes==total. It never tries to assign through an accessor return value. cancel returns false for absent/terminal ids and otherwise sets CANCELED; future ticks do not change canceled progress. get returns a pointer into the queue or nullptr; list returns a defensive copy
- CMakeLists.txt enables C++17 with extensions off; builds downloader_core from exactly src/Url.cpp, src/SafeNamer.cpp, src/Transfer.cpp, src/DownloadQueue.cpp; publishes include; builds downloader_app from src/Main.cpp and downloader_tests from tests/test_main.cpp; links both to downloader_core; calls enable_testing and add_test. No package lookup, fetch, external dependency, network, real filesystem, GUI, thread, clock, sleep, or randomness
- src/Main.cpp constructs an empty existing-files boundary with the literal unambiguous declaration `InMemoryExistingFiles files;`, then constructs FakeTransferAdapter and DownloadQueue, enqueues one fixed https URL, ticks a bounded number of times, and returns 0 without input or a long loop. It never writes `files({})`. tests/test_main.cpp includes only <cassert>, <vector>, "DownloadQueue.h", and "Url.h", defines exactly one int main with exactly four concise blocks: URL/format rules where host-only https://example.com is valid; safe naming with an existing "clip.mp4" yielding "clip_2.mp4"; progress 0->4->8->12 and COMPLETED for total 12/chunk 4; cancellation freezes progress. Empty InMemoryExistingFiles objects in tests also use the zero-argument declaration. Tests never include a .cpp or access private members
- repeat the exact 12-file list, sole DownloadTypes ownership, every direct include including Url.h in DownloadQueue.cpp and <utility> in SafeNamer.cpp, the exact URL host-boundary algorithm and host-only-valid rule, fully declared IExistingFiles, the separate no-argument and vector constructors, forbidden `files({})` form, literal empty declaration, fixed-size ITransferAdapter without sessions/accessor mutation, exact queue signatures/progress algorithm, exact filenames and progress fixtures, CMake targets, four independent test blocks, and all forbidden alias files in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, C++ Build Link Audit, and every affected implementation task
"""
    elif unit["unit_id"] == "p13_video_downloader_python":
        unit_specific_constraints = """


Project-specific Python 3.10 synchronous downloader and cancellation contract:
- use exactly these files and no substitutes, in dependency order: requirements.txt, video_downloader/errors.py, video_downloader/url.py, video_downloader/naming.py, video_downloader/request.py, video_downloader/progress.py, video_downloader/transfer.py, video_downloader/queue.py, video_downloader/__init__.py, Main.py, tests/test_main.py. Do not create models.py, types.py, adapters.py, downloader.py, service.py, or additional source/test files
- errors.py solely defines InvalidURLError(ValueError), InvalidFormatError(ValueError), TransferError(RuntimeError), and CancelledError(RuntimeError). url.py defines validate_url(url:str)->str: require a string, strip only surrounding whitespace, reject embedded whitespace, accept only http/https with nonempty netloc and path, and raise InvalidURLError for every invalid input
- naming.py defines sanitize_filename(name:str)->str and unique_name(base:str,existing:set[str])->str. sanitize_filename strips, changes whitespace runs to underscore, removes path separators and characters outside letters/digits/dot/dash/underscore, trims edge dots/underscores, and falls back to "download". unique_name returns base when free and otherwise appends ` (1)`, ` (2)`, and so on before the extension. The literal fixture unique_name("clip.mp4", {"clip.mp4"}) is exactly "clip (1).mp4"
- request.py defines DownloadRequest with constructor (url:str,fmt:str,output_hint:Optional[str]=None), read-only url/fmt/output_hint properties, and extension()->str. It validates through validate_url, accepts case-insensitive mp4/webm/mkv and stores the lower-case format, raises InvalidFormatError for anything else, sanitizes a supplied output hint, and maps formats to .mp4/.webm/.mkv
- progress.py defines Progress(total:Optional[int]=None) with transferred initially zero, read-only transferred/total properties, update(delta:int), percent()->Optional[float], and add_listener(callback). update rejects negative delta, clamps at total, and synchronously notifies listeners with (transferred,total). It also defines CancellationToken with cancel() and is_cancelled(). No thread, sleep, clock, filesystem, network, or randomness is used
- transfer.py defines frozen dataclass TransferResult(bytes_transferred:int,final_name:str,completed:bool), abstract TransferAdapter with total_bytes(req:DownloadRequest)->int and transfer(req,progress,cancel)->TransferResult, and FakeTransferAdapter(mapping:dict[str,tuple[int,int]]). mapping values are (positive total_bytes, positive chunk_size). total_bytes raises TransferError for an absent URL. transfer derives a sanitized base from output_hint or the URL's final path segment, adds req.extension unless already present, chooses a unique name against an adapter-owned deterministic set, loops in fixed chunks while checking cancellation before each chunk, raises CancelledError if canceled, updates Progress, reserves the completed name, and returns a completed result. It never performs real I/O
- queue.py defines internal mutable _Job and DownloadQueue(adapter). enqueue(req)->int creates sequential ids from 1, a pending job, and Progress(adapter.total_bytes(req)). cancel(job_id)->bool marks a pending job cancelled with zero progress, cancels a running token, and returns false for absent or terminal jobs. process_next()->None processes the first pending job only and skips already-cancelled jobs; it changes pending to running, invokes the synchronous adapter, and records completed/cancelled/failed. process_all()->None repeats until no pending jobs remain. get_status(job_id)->dict returns exactly state, transferred, total, final_name; states are lower-case pending/running/completed/failed/cancelled. Pre-start cancellation is the normative deterministic cancellation fixture; tests MUST NOT demand an impossible external mid-transfer action during a synchronous process_next call
- __init__.py re-exports only the four exceptions, validate_url, sanitize_filename, unique_name, DownloadRequest, Progress, CancellationToken, TransferAdapter, TransferResult, FakeTransferAdapter, and DownloadQueue. Main.py uses absolute imports from video_downloader, exposes run_demo()->dict, uses mapping {"https://example.com/clip": (12,4)}, processes one mp4 request, returns its completed status, and performs no input/network/filesystem/thread activity or mandatory printing. requirements.txt lists only a Python-3.10-compatible pytest requirement
- tests/test_main.py uses exactly four concise tests: (1) run_demo returns a dict with state completed and transferred/total 12/12; (2) validate_url accepts https and rejects ftp/blank with InvalidURLError, and DownloadRequest rejects an invalid format with InvalidFormatError; (3) sanitize_filename("my clip") is "my_clip" and unique_name("clip.mp4", {"clip.mp4"}) is "clip (1).mp4"; (4) use mapping a:(12,4), b:(8,4), enqueue two requests, cancel the first while pending before any process call, process_all, and assert first cancelled with 0/12 and second completed with 8/8 and final_name "b.mp4". Tests never use a real URL transfer and never try to cancel from another execution context
- repeat the exact 11-file list, error ownership, exact URL/naming/request/progress/adapter/queue signatures, pre-start synchronous cancellation rule, exact lowercase states, literal mappings and status fixtures, four-test limit, Python 3.10 compatibility, and absence of external effects in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, and every affected implementation task
"""
    elif unit["unit_id"] == "p14_todo_list_app_java":
        unit_specific_constraints = """


Project-specific Java 11 to-do contract with a deliberately small compile-safe API:
- use exactly these files and no substitutes, in dependency order: pom.xml, src/main/java/Priority.java, src/main/java/Task.java, src/main/java/TaskRepository.java, src/main/java/InMemoryTaskRepository.java, src/main/java/TaskFilter.java, src/main/java/TaskSorter.java, src/main/java/TodoService.java, src/main/java/Main.java, src/test/java/MainTest.java. Every class is in the default unnamed package and no package declaration is allowed. TaskDraft.java, TaskUpdate.java, TaskQuery.java, TaskSort.java, ValidationException.java, TimeProvider.java, TaskSummary.java, and ToDoService.java are forbidden
- target Java 11 exactly with Maven and JUnit Jupiter only. Java records, var in public signatures, Stream.toList(), streams, Optional, builders, custom clock types, external libraries, network, filesystem, GUI, threads, sleep, and randomness are forbidden. Every source directly imports every JDK type it names; do not rely on transitive imports
- the following import audit is literal and binding. Task.java begins with exactly `import java.time.LocalDate;`, `import java.util.ArrayList;`, `import java.util.Collections;`, `import java.util.LinkedHashSet;`, `import java.util.List;`, `import java.util.Locale;`, and `import java.util.Set;`. TaskRepository.java begins with `import java.util.List;`. InMemoryTaskRepository.java begins with `import java.util.ArrayList;`, `import java.util.LinkedHashMap;`, and `import java.util.List;`. TaskFilter.java begins with `import java.util.ArrayList;`, `import java.util.LinkedHashSet;`, `import java.util.List;`, `import java.util.Locale;`, `import java.util.Set;`, and `import java.util.TreeSet;`. TaskSorter.java begins with `import java.time.LocalDate;`, `import java.util.ArrayList;`, `import java.util.Comparator;`, and `import java.util.List;`. TodoService.java begins with `import java.time.LocalDate;`, `import java.util.LinkedHashMap;`, `import java.util.List;`, `import java.util.Map;`, and `import java.util.Set;`. Main.java begins with `import java.time.LocalDate;`, `import java.util.Map;`, and `import java.util.Set;`. MainTest.java directly imports org.junit.jupiter.api.Test, static org.junit.jupiter.api.Assertions.*, java.time.LocalDate, java.util.List, java.util.Map, and java.util.Set. Omitting any used import or using an unqualified symbol without its import is forbidden
- Priority.java solely defines enum Priority { LOW, MEDIUM, HIGH } and public int rank() returning 0, 1, and 2 respectively
- Task.java defines public final class Task. Its exact state is final int id; mutable String title and description; mutable Priority priority; mutable LocalDate dueDate; mutable LinkedHashSet<String> tags; mutable boolean completed. The exact public constructor is Task(int id,String title,String description,Priority priority,LocalDate dueDate,Set<String> tags). It rejects id<=0, null/blank trimmed title, and null priority with IllegalArgumentException; null description becomes the empty string; dueDate may be null. Its own private static LinkedHashSet<String> normalizeTags(Set<String>) uses trim and toLowerCase(Locale.ROOT), removes blanks/duplicates, sorts lexicographically, and returns a LinkedHashSet. It exposes getId(), getTitle(), getDescription(), getPriority(), getDueDate(), getTags(), isCompleted(), edit(String,String,Priority,LocalDate,Set<String>), and setCompleted(boolean). getTags returns exactly `Collections.unmodifiableSet(new LinkedHashSet<>(tags))`. edit applies the same validation and normalization. There is no builder, no Optional, no final mutable field assignment, and no ternary expression whose branch is an exception object
- TaskRepository.java is an interface with exact methods void add(Task task), Task findById(int id) returning null when absent, void save(Task task), boolean deleteById(int id), and List<Task> findAll(). InMemoryTaskRepository.java holds a LinkedHashMap<Integer,Task>; add rejects null or duplicate id, save rejects null or absent id, delete returns whether an entry existed, and findAll returns a defensive ArrayList sorted by id ascending. Use simple loops/lambdas and explicit imports only
- TaskFilter.java is a utility with exact static List<Task> filter(List<Task> tasks,Boolean completed,Priority priority,Set<String> requiredTags). A null Boolean or Priority means no constraint. TaskFilter declares and uses its own private static LinkedHashSet<String> normalizeRequiredTags(Set<String>) implemented with trim, toLowerCase(Locale.ROOT), TreeSet, and LinkedHashSet; it MUST NOT call Task.normalizeTags or any other private Task method. Every requested normalized tag must be present. It returns a new list in input order and never mutates tasks or the input list
- TaskSorter.java is a utility with exact static List<Task> sort(List<Task> tasks). It copies the input and applies one literal comparator lambda or anonymous Comparator with these comparisons in this exact order: higher priority rank first; non-null due dates before null due dates and real dates ascending; case-insensitive title; id ascending. Implement comparisons with Integer.compare, LocalDate.compareTo, and String.CASE_INSENSITIVE_ORDER.compare only. Collections.reverseOrder, Comparator.comparing/thenComparing/reversed, chained or compound comparators, streams, TaskSort.Key, and any configurable sort-key abstraction are forbidden
- TodoService.java owns TaskRepository repository and int nextId initialized to 1. Its exact API is Task createTask(String title,String description,Priority priority,LocalDate dueDate,Set<String> tags); Task editTask(int id,String title,String description,Priority priority,LocalDate dueDate,Set<String> tags); boolean deleteTask(int id); Task setCompleted(int id,boolean completed); List<Task> listTasks(Boolean completed,Priority priority,Set<String> requiredTags); Map<String,Integer> summary(LocalDate today). createTask MUST literally execute in this order: `Task task = new Task(nextId, title, description, priority, dueDate, tags);`, then `repository.add(task);`, then `nextId += 1;`, then `return task;`. Pre-increment, post-increment, incrementing before construction/save, and consuming an id after any failed create are forbidden; therefore after a rejected blank-title create, the first valid task still has id 1. editTask/setCompleted throw IllegalArgumentException for a missing id. listTasks is exactly TaskSorter.sort(TaskFilter.filter(repository.findAll(),completed,priority,requiredTags)). summary rejects null today and returns a LinkedHashMap with keys inserted exactly total, completed, pending, overdue; overdue counts only incomplete tasks with non-null dueDate strictly before today
- Main.java exposes public static Map<String,Integer> runDemo() and public static void main(String[] args). runDemo creates a fresh repository/service, creates exactly Write paper at HIGH due 2023-10-14 with work/urgent tags and marks it complete, creates Buy milk at MEDIUM due 2023-10-16 with home tag and leaves it incomplete, then returns summary(LocalDate.of(2023,10,15)); therefore the exact result is total2, completed1, pending1, overdue0. main only calls runDemo and returns normally with no System.exit and no input
- pom.xml uses source/target 11, UTF-8, JUnit Jupiter 5.9.3 test scope, and Maven Surefire 3.1.2 with useModulePath false. MainTest.java is in the unnamed package, imports only JUnit plus JDK collection/date classes, and contains exactly four concise @Test methods: runtime/demo, CRUD/validation, filter/sort, and summary. Runtime calls Main.main(new String[0]) and checks the exact runDemo result. CRUD rejects a blank title, creates Alpha as id1, edits it to Beta, completes and deletes it. Filter/sort creates Low due 2023-10-16 tagged work, High due 2023-10-17 tagged work/urgent, and Medium with null due date tagged home; filtering incomplete tasks requiring work yields High then Low. Summary at 2023-10-15 uses one incomplete HIGH task due 2023-10-14, one incomplete LOW task due 2023-10-16, and one completed MEDIUM task due 2023-10-14, producing total3, completed1, pending2, overdue1
- repeat the exact 10-file list, default-package rule, Java-11 bans, exact fields/signatures, null-versus-exception behavior, simple sorting algorithm, summary keys, demo values, four test scopes, and all forbidden alias files in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, and every affected implementation task
"""
    elif unit["unit_id"] == "p14_todo_list_app_python":
        unit_specific_constraints = """


Project-specific Python 3.10 to-do priority/error and deterministic-date contract:
- use exactly these files and no substitutes, in dependency order: requirements.txt, todo_app/errors.py, todo_app/priority.py, todo_app/entities.py, todo_app/filtering.py, todo_app/sorting.py, todo_app/repository.py, todo_app/clock.py, todo_app/service.py, todo_app/__init__.py, Main.py, tests/test_main.py. Do not add models.py, types.py, exceptions.py, utils.py, or additional source/test files
- errors.py solely defines class ValidationError(Exception) with an ordinary message constructor and class NotFoundError(ValidationError). priority.py directly contains `from .errors import ValidationError`, uses enum.Enum (not IntEnum), and defines Priority members LOW, MEDIUM, HIGH plus order_value()->int returning 0/1/2. Priority.from_value accepts an existing Priority unchanged or a string after strip/lower; low maps LOW, med/medium maps MEDIUM, high maps HIGH; every other value raises ValidationError, never ValueError, TypeError, KeyError, or another built-in exception
- entities.py defines mutable dataclass Task with id:int, title:str, optional description, Priority, optional datetime.date due_date, normalized list[str] tags, completed=False, completed_at=None. Title is stripped and nonblank or ValidationError. Tags are stripped, lowercased, empty removed, deduplicated, and sorted. mark_complete_on(day) is idempotent and preserves the first completed_at; mark_incomplete clears it
- filtering.py defines TagMatchMode ANY/ALL, FilterCriteria, and pure filter_tasks. sorting.py defines SortKey DUE_DATE/PRIORITY/TITLE/COMPLETED, SortDirection ASC/DESC, and pure stable sort_tasks with final id-ascending tie break; for DUE_DATE, real dates precede None in ascending order. No function mutates input tasks
- repository.py defines TaskRepository ABC and InMemoryTaskRepository with sequential ids starting at 1, deterministic id-sorted list_all, duplicate ValidationError, and missing-id NotFoundError. clock.py defines Clock ABC, SystemClock, and FixedClock(fixed:date); tests use only FixedClock and never wall time
- service.py directly imports ValidationError and Priority. ApplicationService.create_task calls Priority.from_value for strings and propagates its ValidationError, assigns repo.next_id, stores and returns Task. It provides edit/complete/uncomplete/delete/list_tasks/summary; complete is idempotent. summary returns exactly total, completed, pending, by_priority with uppercase LOW/MEDIUM/HIGH string keys, and completed_today using clock.today
- __init__.py explicitly re-exports ValidationError, NotFoundError, Priority, Task, TagMatchMode, FilterCriteria, filter_tasks, SortKey, SortDirection, sort_tasks, TaskRepository, InMemoryTaskRepository, Clock, SystemClock, FixedClock, and ApplicationService. Main.py uses absolute imports from todo_app, exposes run_demo()->dict with a fixed date and exits without input/network/filesystem/GUI/thread activity. requirements.txt lists a Python-3.10-compatible pytest only
- tests/test_main.py has exactly four concise pytest tests using only public todo_app imports plus datetime.date and run_demo from Main: (1) run_demo is a dict and ordinary create/complete/list works with FixedClock(date(2023,10,15)); (2) `service.create_task("Test", priority="invalid")` raises ValidationError specifically; (3) equal due date tasks sort by id ascending; (4) completing twice preserves completed_at and summary has total1/completed1/pending0/completed_today1 plus uppercase priority counts. Tests never catch ValueError as an alternative
- repeat the exact 12-file list, direct priority-to-errors import, Enum/non-IntEnum rule, exact from_value mapping and ValidationError-only failure, task normalization/idempotence, deterministic sorting/repository/clock, exact summary keys, public exports, four-test limit and literal fixtures in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, and every affected implementation task
"""
    elif unit["unit_id"] == "p14_todo_list_app_cpp":
        unit_specific_constraints = """


Project-specific C++17 to-do repository and header-self-containment contract:
- use exactly these files and no substitutes, in dependency order: CMakeLists.txt, include/Task.h, src/Task.cpp, include/Date.h, src/Date.cpp, include/Query.h, src/Query.cpp, include/TaskStore.h, src/TaskStore.cpp, include/TaskManager.h, src/TaskManager.cpp, src/Main.cpp, tests/test_main.cpp. Do not add separate Priority, Filter, Sort, Repository, Service, Controller, or exception files
- every header is self-contained. Task.h directly includes <cstdint>, <string>, and <vector>. Date.h directly includes <string>. Query.h directly includes <optional>, <string>, <vector>, "Date.h", and "Task.h". TaskStore.h directly includes <cstdint>, <map>, <vector>, and "Task.h" before declaring `std::map<std::uint64_t, Task> tasks_`. TaskManager.h directly includes <cstddef>, <cstdint>, <string>, <utility>, <vector>, "Query.h", and "TaskStore.h". Never rely on a transitive standard-library include
- Task.cpp directly includes "Task.h", <algorithm>, and <cctype>. Date.cpp directly includes "Date.h" and <cctype>; every anonymous-namespace helper is declared before first use: in particular `IsLeapYear` MUST be defined or forward-declared before `IsValidDay` calls it, and a call to an as-yet undeclared helper is forbidden. Query.cpp directly includes "Query.h", <algorithm>, and <set>; every use of `std::set` therefore compiles. TaskStore.cpp directly includes "TaskStore.h". TaskManager.cpp directly includes "TaskManager.h", <algorithm>, and <stdexcept>. Sources and tests include project headers only by basename and never include a .cpp file
- Task.h solely defines enum class Priority { Low, Medium, High } and aggregate Task with std::uint64_t id, string title/description/due_date, Priority priority, vector<string> tags, and bool completed, plus static Trim, NormalizeTag, NormalizeTags, and IsValidTitle helpers. NormalizeTags removes empty tags, sorts, and deduplicates deterministically
- DateRules exposes static bool is_valid_iso_date(const std::string&) and static int compare_dates(const std::string&,const std::string&). Dates are exactly YYYY-MM-DD with digit and month/day range checks. TaskManager permits an empty due date; Query sorts an empty due date after valid dates. Consequently compare_dates("", valid_date) returns positive, compare_dates(valid_date, "") returns negative, and compare_dates("", "") returns zero
- Query.h declares its public types at global/namespace scope in this exact order: first `enum class SortOrder { ByDueThenPriority, ByTitle };`, then struct FilterOptions with optional completed/min_priority/due_before/due_after and vector<string> require_tags, then class Query with static WithTags/matches/less_due_priority/less_title. SortOrder MUST remain outside class Query; nesting it in Query and spelling `Query::SortOrder` anywhere are forbidden. TaskManager.h and TaskManager.cpp use the unqualified global name SortOrder. Query requires every requested normalized tag, sorts earlier valid due dates first, then higher priority, title, and id deterministically
- TaskStore.h owns ITaskStore and concrete InMemoryTaskStore backed only by the private map tasks_. Its add/update/remove/find/get_all methods return ordinary success values, pointers into the map only for find, and an ascending-id defensive vector for get_all
- TaskManager owns an injected ITaskStore reference and monotonically increasing IDs starting at 1. create_task validates title and optional due date, normalizes tags, stores completed=false, and returns the id; edit_task revalidates; delete_task and set_completed return false for missing ids; list filters and sorts copies; summarize returns pair<completed_count,pending_count>
- CMakeLists.txt enables C++17 with extensions off, builds todo_core from the five non-Main source files, publishes the include directory, builds todo_app and todo_tests, links both to todo_core, calls enable_testing(), and registers todo_tests. No external package, FetchContent, framework, filesystem, network, GUI, thread, clock, or randomness is allowed
- src/Main.cpp performs one small fixed non-interactive demo and returns 0. tests/test_main.cpp directly includes <cassert>, <stdexcept>, <vector>, and "TaskManager.h", defines exactly one int main(), and has exactly three fresh-object blocks: basic create/list/summary, invalid title/date rejection, and normalized-tag plus due-date/priority ordering. Each block is independently scoped and MUST NOT reference a local id declared in another block. The invalid-title/date block first creates its own local valid task as `const auto existing_id = manager.create_task("Existing", "", "", Priority::Low, {});` and uses existing_id when asserting that edit_task throws for invalid replacement data; it uses an arbitrary missing id only for the false-return assertion. It uses no third-party test framework. Because assert is a preprocessor macro, a braced initializer containing a comma must never appear directly inside assert: `assert(actual == std::vector<std::string>{"a", "b"});` is forbidden. Instead first declare `const std::vector<std::string> expected_tags{"a", "b"};` and then call `assert(actual == expected_tags);`; double-parenthesized assert is permitted but a named expected vector is preferred
- repeat the exact 13-file list, all direct include lists (especially TaskStore.h <map> and Query.cpp <set>), helper declaration-before-use rule, empty-date comparison signs, global non-nested SortOrder declaration and unqualified use, exact field names, canonical APIs, deterministic ordering, independent test-block variable ownership including local existing_id, the forbidden braced-initializer-inside-assert form and named expected-vector replacement, one-main test rule, and three scopes in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, C++ Build Link Audit, and every affected implementation task
"""
    elif unit["unit_id"] == "p02_flappy_bird_game_python":
        unit_specific_constraints = """


Project-specific deterministic behavior and test contract:
- Game begins in state \"ready\"; flap() in \"ready\" must atomically change the state to \"running\" and immediately apply config.flap_impulse, while flap() in \"running\" reapplies the impulse and flap() in \"game_over\" is a no-op
- a running step first updates vertical velocity as clamp(vy + gravity, -max_vy, max_vy), then updates y by that velocity; therefore after an initial -8.0 flap and +0.5 gravity, one step exposes vy=-7.5 and a lower y
- during each running step, move pipes, mark and score every unpassed pipe whose right edge is strictly left of bird_x exactly once, and only then remove off-screen pipes; passed remains observably true while that pipe remains in pipes_readonly()
- make scoring independently testable with one precisely named pure helper and specify its exact signature in the Full API; unit-test that helper with a handcrafted pipe instead of waiting through a long Game loop
- tests/test_main.py must contain only 2 to 4 short deterministic tests and must not advance dozens of ticks to test scoring, because gravity/collision makes such a test depend on unrelated mechanics
- use only the canonical states \"ready\", \"running\", and \"game_over\" and repeat these state, flap, integration, scoring-order, and test rules in the Full API specification and every affected file task
"""
    elif unit["unit_id"] == "p03_game_2048_python":
        unit_specific_constraints = """


Project-specific Python 3.10 import and deterministic-test contract:
- Main.py is a top-level module imported by pytest as from Main import run_demo; therefore Main.py MUST use absolute imports beginning with from twenty48, specifically from twenty48.game import Game and from twenty48.types import Direction, and MUST NEVER use from .twenty48, any leading-dot import, or assume the repository root is a package
- modules inside the twenty48 package may use explicit package-relative imports such as from .types import Direction; twenty48/__init__.py may re-export Board, Game, Direction, and GameStatus with package-relative imports
- expose exactly run_demo(seed: int = 0) -> dict in Main.py; it creates Game(seed), calls reset once, applies Direction.LEFT once, returns a dictionary containing status, score, and tiles, prints at most one concise line, performs no input/network/GUI work, and Main.py invokes it only under the if __name__ == "__main__": guard
- keep the canonical pure function move_line_left(line: list[int]) -> tuple[list[int], int]; it validates length four, compacts zeroes, merges each tile at most once from left to right, and reports the sum of newly merged values
- move_line_left MUST use the unambiguous output-list algorithm literally: set values=[v for v in line if v!=0] (not line[:] and not any copy retaining zeroes), output=[], score=0, i=0; while i<len(values), if i+1<len(values) and values[i]==values[i+1], append values[i]*2, add that merged value to score, and execute i+=2, otherwise append values[i] and execute i+=1; finally append zeroes until output has length four and return (output,score)
- an in-place pop algorithm is forbidden: never merge by replacing values[i] and popping values[i+1], never increment i twice after a merge, and never leave i unchanged after a merge, because either pattern skips an independent pair or lets a newly merged tile merge again in the same move
- tests/test_main.py contains exactly 2--4 concise tests and uses only absolute imports: from Main import run_demo and from twenty48.move import move_line_left; leading-dot imports and dynamically changing sys.path are forbidden
- the exact pure fixtures are move_line_left([2,2,2,0]) == ([4,2,0,0],4), move_line_left([2,2,4,4]) == ([4,8,0,0],12), and the mandatory gap-compaction fixture move_line_left([2,0,2,0]) == ([4,0,0,0],4); tests must include all three so an implementation that scans an uncompressed copy cannot pass; a smoke test calls run_demo(0) and only checks that the result is a dict with keys status, score, and tiles, avoiding brittle random-position expectations
- requirements.txt contains only a Python-3.10-compatible pytest requirement; never list the standard library or the local twenty48 package as an external dependency
- repeat the top-level absolute-import rule, forbidden leading-dot Main import, exact run_demo API, exact zero-filtering output-list merge pseudocode with i+=2/i+=1, forbidden in-place-pop and zero-retaining implementations, all three exact pure fixtures including gap compaction, and test imports in Full API specification, Logic Analysis, Test Scope Plan, Shared Knowledge, and the Main.py/twenty48/move.py/tests/test_main.py implementation tasks; merely saying that Main depends on twenty48 or that tiles merge once is insufficient
"""
    elif unit["unit_id"] == "p03_game_2048_cpp":
        unit_specific_constraints = """


Project-specific C++ compilation contract:
- every header that declares a size or index type must include <cstddef> directly and spell the type std::size_t; bare size_t is forbidden
- repeat the <cstddef>/std::size_t rule in the Full API specification and in every affected header/source implementation task
- do not rely on transitive standard-library includes, and do not use an integer shift whose width equals or exceeds the left operand's width
"""
    priority_footer = ""
    if unit["unit_id"] == "p05_brick_breaker_game_cpp":
        priority_footer = """

FINAL NON-NEGOTIABLE BRICK-BREAKER C++ COMPILATION CHECKLIST:
- Full API specification, Logic Analysis, Shared Knowledge, and every Level/GameEngine task must each preserve the literal tokens `#include <cstddef>` and `std::size_t` for Level::remaining and GameEngine::remainingBricks.
- The src/GameEngine.cpp contract must literally say it directly contains `#include "Collision.h"` and `#include <cmath>`, and every square-root call is `std::sqrt`. The implementation must not depend on transitive includes.
- Do not summarize or omit any literal include/type token in this final checklist; the architecture is invalid without all five tokens.
"""
    elif unit["unit_id"] == "p05_brick_breaker_game_python":
        priority_footer = """

FINAL NON-NEGOTIABLE BRICK-BREAKER PYTHON IMPORT CHECKLIST:
- Task filenames are exactly: requirements.txt; brick_breaker/config.py; brick_breaker/ball.py; brick_breaker/paddle.py; brick_breaker/brick.py; brick_breaker/level.py; brick_breaker/collision.py; brick_breaker/game.py; brick_breaker/__init__.py; Main.py; tests/test_main.py.
- Full API must literally contain `brick_breaker/config.py: class GameConfig` and `from .config import GameConfig` for both level.py and game.py.
- config.py is the sole GameConfig owner and imports no project module; level.py never imports `.game` or brick_breaker.game; __init__.py imports GameConfig from `.config`. The architecture is invalid if these ownership/import rules are summarized away.
"""
    elif unit["unit_id"] == "p06_tank_battle_game_java":
        priority_footer = """

FINAL NON-NEGOTIABLE TANK-BATTLE JAVA COMPILATION CHECKLIST:
- Task filenames are exactly: pom.xml; src/main/java/Position.java; src/main/java/Orientation.java; src/main/java/Command.java; src/main/java/Tank.java; src/main/java/Projectile.java; src/main/java/ObstacleMap.java; src/main/java/Arena.java; src/main/java/ScoreBoard.java; src/main/java/GameEngine.java; src/main/java/Main.java; src/test/java/MainTest.java.
- Full API and implementation tasks must literally preserve `private Position position;` in Tank and Projectile, `private Orientation orientation;` in Tank, `void setPosition(Position position)` in Projectile, `void reset(Collection<String> tankIds)` in ScoreBoard, and `scoreBoard.reset(initialTanks.keySet())` in GameEngine; GameEngine never accesses ScoreBoard fields directly. Tank permits `health==0`, rejects only `health<0`, and copy() must successfully copy a dead tank; GameEngine separately rejects a non-alive initial tank.
- GameEngine literally owns `private Arena arena;`, `private final Arena initialArena;`, `private Map<String,Tank> tanks;`, `private final Map<String,Tank> initialTanks;`, and `private final ScoreBoard scoreBoard;`; `tanks` is the current state while initialTanks is a preserved deep snapshot. Its constructor literally creates `Tank initialCopy = tank.copy();` and a separate `Tank currentCopy = tank.copy();`, then puts initialCopy only in initialTanks and currentCopy only in tanks; putting one copied object in both maps is forbidden. All game actions and getters use `tanks`. reset may assign the non-final current arena with `this.arena = initialArena.copy();` and MUST assign `this.tanks = new HashMap<>();` before copying every initialTanks.values() entry into `this.tanks`; it must never clear or mutate initialTanks. Java streams and Collectors are forbidden, reset iterates initialTanks.values(), and Main uses fully qualified `java.util.Arrays.asList(...)` rather than an unimported Arrays symbol.
- MainTest never reads constructor-input `alice` or `bob` after constructing GameEngine; after blocked movement, after turning, after reset, and after firing it locates the relevant tank in a fresh `engine.getTanksCopy()` result. It never retains a tank copy across tick or reset.
- Full API must spell the same-tick projectile fixture Position(1,2) -> spawn Position(2,2) -> hit Bob at Position(3,2), and MainTest has exactly three tests with fresh defensive copies, score hits1/kills1/total6, and no second kill shot. Do not summarize or substitute these compile and fixture rules.
"""
    elif unit["unit_id"] == "p06_tank_battle_game_python":
        priority_footer = """

FINAL NON-NEGOTIABLE TANK-BATTLE ARCHITECTURE CHECKLIST:
- Task list filenames are exactly: requirements.txt; tank_battle/directions.py; tank_battle/geometry.py; tank_battle/obstacle.py; tank_battle/arena.py; tank_battle/tank.py; tank_battle/projectile.py; tank_battle/commands.py; tank_battle/scoring.py; tank_battle/game.py; tank_battle/configs.py; tank_battle/__init__.py; Main.py; tests/test_main.py.
- Full API must contain these literal strings: `id:str`, `owner_id:str`, `tanks:dict[str,Tank]`, `player_id:str`, `build_default_demo()->Game`, `record_hit`, `record_kill`, `score(player_id)=hits+5*kills`, `steps<1`, `Arena(8,5,[])`, `Tank("p1","P1",1,2,Direction.E,3,1)`, and `Tank("p2","P2",6,2,Direction.W,3,1)`.
- Full API must also contain the literal Enum tokens `from enum import Enum`, `class Direction(Enum):`, `N=(0,-1)`, `E=(1,0)`, `S=(0,1)`, and `W=(-1,0)`; snapshot values are only plain dict/list/scalars and directions serialize through `.name`.
- Full API and game.py task must literally contain `ScoreBoard(player_ids:list[str])`, `ScoreBoard(list(self._initial_tanks))`, `from .commands import Command, MoveForward, RotateLeft, RotateRight, RotateTo, Fire`, `self.scores.record_hit(projectile.owner_id)`, and `self.scores.record_kill(projectile.owner_id)`; hits and kills contain every initial player id with value zero before events.
- Full API must literally say `Command has no execute method` and `Game.tick dispatches solely with isinstance`; commands.py must not use ABC or @abstractmethod, no command class may define execute, and game.py must never call command.execute.
- configs.py is the sole build_default_demo owner, __init__.py imports it from .configs, and Main.py literally uses `from tank_battle import build_default_demo, RotateRight` plus `game.queue_command("p1", RotateRight())`, never a command-name string; build_default_demo returns that exact Game, run_demo calls tick once, a new Fire projectile moves from (2,2) to (3,2) during that same tick and hits p2 at (4,2) on the next tick, reset restores a deep initial snapshot with hits/kills exactly `{"p1":0,"p2":0}` rather than empty dictionaries, the reset test captures initial immediately after Game construction with no prior Fire or tick, tests use absolute imports, and Test Scope Plan contains exactly four rows: runtime, obstacle, projectile-hit/scoring, and reset using the literal fixtures already specified above. Do not summarize, rename, weaken, or substitute any item in this final checklist.
"""
    elif unit["unit_id"] == "p07_calculator_python":
        priority_footer = """

FINAL NON-NEGOTIABLE CALCULATOR PYTHON OWNERSHIP CHECKLIST:
- Task filenames are exactly: requirements.txt; calculator/errors.py; calculator/history.py; calculator/tokenizer.py; calculator/engine.py; calculator/api.py; calculator/__init__.py; Main.py; tests/test_main.py.
- tokenizer.py solely defines Token, NumberToken, OpToken, LParenToken, RParenToken, and Tokenizer. Its sole project import is `from .errors import TokenizationError`; `from .tokenizer import` and `from calculator.tokenizer import` are forbidden inside tokenizer.py, and token classes are never reassigned to object.
- engine.py literally imports `from .tokenizer import Token, NumberToken, OpToken, LParenToken, RParenToken`; dependencies remain errors/history -> tokenizer -> engine -> api -> __init__/Main/tests with no reverse edge.
- MainTest contains exactly three tests with the fixed arithmetic/history/error fixtures. It may assert only `len(tokenize("1 + 2.5")) == 3`; token isinstance checks, internal token imports, reflection, token construction, and `type(tokens[0])()` are forbidden. Do not summarize or substitute these ownership, import, or test constraints.
"""
    elif unit["unit_id"] == "p08_excel_data_processing_java":
        priority_footer = """

FINAL NON-NEGOTIABLE EXCEL-PROCESSING JAVA 11 CHECKLIST:
- Task filenames are exactly: pom.xml; src/main/java/ProcessingReport.java; src/main/java/Cell.java; src/main/java/Row.java; src/main/java/Sorters.java; src/main/java/Sheet.java; src/main/java/Workbook.java; src/main/java/ValueParser.java; src/main/java/Filters.java; src/main/java/Aggregations.java; src/main/java/CsvIO.java; src/main/java/Main.java; src/test/java/MainTest.java.
- Java streams and `Stream.toList()` are forbidden. CsvIO has only `Sheet importCsvFromString(String name, String csv, ProcessingReport report)` and `String toCsvString(Sheet sheet, ProcessingReport report)`; import alone increments rowsRead and export alone increments rowsWritten, once per data row.
- Every aggregation calls ValueParser once per row. The invalid-data test calls sum exactly once with a fresh report and therefore records Sales invalid count exactly 1. Every import, filter, aggregation, export, and re-import phase in tests uses its own fresh ProcessingReport.
- MainTest is in the unnamed package and imports no project class. It contains exactly three loop-based tests: Main.main runtime, the exact three-row Country/Sales pipeline, and the exact four-row invalid/round-trip fixture. The four name assertions literally traverse Row -> Cell -> raw using `filteredRows.get(0).get("Name").raw()`, `filteredRows.get(1).get("Name").raw()`, `sortedRows.get(0).get("Name").raw()`, and `sortedRows.get(1).get("Name").raw()`; direct Row.raw() is forbidden. It never expects rowsKept/rowsWritten from import and never calls average/min/max on the report used for the one-invalid sum assertion. Do not summarize or substitute these contracts.
"""
    elif unit["unit_id"] == "p08_excel_data_processing_python":
        priority_footer = """

FINAL NON-NEGOTIABLE EXCEL-PROCESSING PYTHON IMPORT CHECKLIST:
- Task filenames are exactly: requirements.txt; excel_processor/model.py; excel_processor/operations.py; excel_processor/csv_io.py; excel_processor/report.py; excel_processor/__init__.py; Main.py; tests/test_main.py.
- model.py is the sole owner of Cell, Row, and Sheet and imports no project module. operations.py, csv_io.py, and report.py may import only `.model`; model.py must never import those modules. The old split modules sheet.py/row.py/cell.py/filter.py/sort.py and wrapper classes Filter/Sorter/ReportGenerator/CSVUtils are forbidden.
- Tests contain exactly three cases and preserve the literal four-row operation fixture, the predicate `lambda row: isinstance(row.values()[0], (int, float)) and row.values()[0] >= 2`, and `loads_csv("name,value\\nA,1\\nB,\\n")` round-trip fixture. Do not summarize or substitute these ownership, import, API, and fixture rules.
"""
    elif unit["unit_id"] == "p09_qr_code_gen_det_cpp":
        priority_footer = """

FINAL NON-NEGOTIABLE QR C++17 CHECKLIST:
- Every role outputs only fields from its current `nodes` schema. The Architect sets `Data structures and interfaces` and `Program call flow` to empty strings and does not emit Full API, Logic Analysis, Test Scope Plan, Shared Knowledge, C++ Build Link Audit, or Task list; the ProjectManager emits those later. Keep JSON strings single-line and emit no Mermaid, code fence, multiline code sample, or raw function body.
- Task filenames are exactly: CMakeLists.txt; include/QRMatrix.h; src/QRMatrix.cpp; include/QRCodec.h; src/QRCodec.cpp; include/QRRenderer.h; src/QRRenderer.cpp; src/Main.cpp; tests/test_main.cpp. BinaryEncoder, QRLayout, QREncoder, QRValidator, and QRDetector files are forbidden.
- Headers are self-contained. QRMatrix.h directly includes <array>, <cstddef>, <stdexcept>; QRCodec.h and QRRenderer.h directly include <string> and "QRMatrix.h". Sources/tests include basename headers, never include/... or .cpp files. CMake publishes the include directory and links app/tests to qr_core.
- QRMatrix is fixed 21x21 with three exact 5x5 markers, no separators; exactly 366 other cells are payload positions in row-major order. Wire format is length8, text bytes MSB-first, checksum8=sum(text bytes)%256, then all-zero padding; text length is at most 40.
- Tests define one int main and exactly three blocks. Corruption is literally `QRMatrix corrupted = matrix;` followed by `corrupted.set(0, 0, false);`; setting [0][0] true is forbidden because true is already valid. Round-trip text is hello-\u4e16\u754c, render contains exactly 20 newlines, and 41 bytes are rejected. Do not summarize or substitute these rules.
"""
    elif unit["unit_id"] == "p09_qr_code_gen_det_java":
        priority_footer = """

FINAL NON-NEGOTIABLE QR JAVA PADDING CHECKLIST:
- Task filenames are exactly: pom.xml; src/main/java/QRMatrix.java; src/main/java/Checksum.java; src/main/java/ZigZag.java; src/main/java/FinderPattern.java; src/main/java/TextEncoder.java; src/main/java/MatrixValidator.java; src/main/java/QRDetector.java; src/main/java/QRCodec.java; src/main/java/QRRenderer.java; src/main/java/Main.java; src/test/java/MainTest.java.
- Full API and affected implementation tasks literally contain `byte[] result = new byte[(bits.length + 7) / 8];`, `result[i / 8] |= (byte) (1 << (7 - (i % 8)));`, and `byte[] frame = java.util.Arrays.copyOf(bytes, frameLength);`. bitsToBytes accepts non-byte-aligned arrays and never rejects `bits.length % 8 != 0`.
- Checksum covers only the two-byte length and UTF-8 payload prefix: encodePayload and decodePayload both literally use `java.util.Arrays.copyOf(frame, frame.length - 1)` as the Checksum.sumMod256 input and compare against the unsigned final byte. Computing the validation checksum over the complete frame is forbidden. bytesToBits literally uses `bits[i * 8 + bit] = (bytes[i] & (1 << (7 - bit))) != 0;`.
- ZigZag.traversal first counts only unreserved cells and literally allocates `int[][] result = new int[count][2];`, then fills it with two bounded row/column for-loop passes: columns ascend on even rows and descend on odd rows. `new int[size * size][2]`, `index < size * size`, every while loop, and placeholder coordinates are forbidden; encode and decode consume the returned coordinates directly without testing reserved a second time.
- QRDetector reads all unreserved bits, converts all of them with the padding implementation, obtains L from the first two bytes, sets `int frameLength = 2 + length + 1;`, truncates to that frame, validates it, and ignores only the unused zero matrix suffix. It never sends all capacity bytes into exact-length decodePayload.
- MatrixValidator supports odd sizes at least 21 and computes capacity from the actual reserved mask. QRCodec auto-size literally begins `int size = 21;` and never reads MatrixValidator.MIN_SIZE or another constant.
- MainTest is in the default package and imports only JUnit Test/Assertions; importing QRCodec, QRMatrix, TextEncoder, QRRenderer, Main, or any other unnamed-package class is forbidden. MainTest has exactly three tests and literally checks the nine-bit input `new boolean[]{true,false,false,false,false,false,false,false,true}` yields unsigned bytes 128 and 128, directly checks `TextEncoder.decodePayload(TextEncoder.encodePayload("hello-\u4e16\u754c"))`, round-trips the matrix codec, and rejects a copied matrix whose finder cell `[0][0]` is flipped. Do not summarize or substitute these statements or fixtures.
"""
    elif unit["unit_id"] == "p09_qr_code_gen_det_python":
        priority_footer = """

FINAL NON-NEGOTIABLE QR PYTHON CODEC CHECKLIST:
- Task filenames are exactly: requirements.txt; qr_code/payload.py; qr_code/matrix.py; qr_code/codec.py; qr_code/render.py; qr_code/__init__.py; Main.py; tests/test_main.py.
- `bytes` is always the Python built-in and must never be imported from typing. SIZE=21 and FINDER_SIZE=5 are fixed; payload bits are length8 + UTF-8 data bits + checksum8, and tests contain exactly three cases.
- extract_bits returns all 366 non-finder bits; unpack_payload parses the length-determined prefix, requires all trailing matrix padding to be zero, and ignores that zero padding. codec.decode passes extract_bits(matrix) directly to unpack_payload and must never regroup the 366 bits into bytes itself.
- Tests preserve `generate("hello-\u4e16\u754c")`, exact round-trip decoding, 21x21 validation/rendering, `[row[:] for row in matrix]`, corrupted[0][0] finder rejection, and malformed 2x2 rejection. Do not summarize or substitute the wire format, API, or fixtures.
"""
    elif unit["unit_id"] == "p10_crud_system_cpp":
        priority_footer = """

FINAL NON-NEGOTIABLE CRUD C++17 CHECKLIST:
- Task filenames are exactly: CMakeLists.txt; include/Record.h; src/Record.cpp; include/ManualClock.h; src/ManualClock.cpp; include/Repository.h; src/Repository.cpp; include/CrudService.h; src/CrudService.cpp; src/Main.cpp; tests/test_main.cpp. Id/Clock/Query/Audit/MemoryRepository and abstract interface files are forbidden.
- Every header includes its own standard/project dependencies. In particular Repository.h directly includes <map>, <optional>, <string>, <vector>, and "Record.h"; CrudService.h directly includes <optional>, <string>, <vector>, "ManualClock.h", "Record.h", and "Repository.h". Sources use basename header includes.
- Record fields are exactly id/name/email/revision/updated_at; ManualClock is deterministic; Repository is a concrete std::map store; CrudService create/update/remove/get/list uses the specified exceptions, revision, and timestamps.
- tests/test_main.cpp contains exactly one int main with exactly three fresh-object blocks: CRUD at times 100/105, invalid/duplicate rejection, and deterministic id order a then b. No default-constructor duplication, transitive includes, wall clock, external test framework, or invented field spelling is allowed. Do not summarize or substitute these rules.
"""
    elif unit["unit_id"] == "p10_crud_system_python":
        priority_footer = """

FINAL NON-NEGOTIABLE CRUD PYTHON 3.10 PAGINATION CHECKLIST:
- Task filenames are exactly: requirements.txt; crud_system/errors.py; crud_system/types.py; crud_system/clock.py; crud_system/validation.py; crud_system/repository.py; crud_system/search.py; crud_system/audit.py; crud_system/service.py; crud_system/__init__.py; Main.py; tests/test_main.py.
- types.py declares an ordinary non-generic dataclass `class Page:` with items:list[Item], total:int, limit:int, offset:int. TypeVar, Generic, Page[Item], and subscribing Page in any annotation are forbidden.
- search.py uses exactly `paginate(items:list[Item],limit:int|None=None,offset:int=0)->Page`; importing crud_system under Python 3.10 must succeed. repository.py directly imports DuplicateNameError and NotFoundError from .errors.
- AuditTrail() takes no clock. Service alone calls FixedClock.now exactly once per create/update/delete and reuses that one timestamp for both entity and audit. Tests contain exactly three cases with create/update times 100/110, explicit duplicate/missing errors, and Alpha/Beta/Gamma pagination plus audit times [100,110,120]. Do not summarize or substitute these rules.
"""
    elif unit["unit_id"] == "p10_crud_system_java":
        priority_footer = """

FINAL NON-NEGOTIABLE CRUD JAVA 11 COMPILATION CHECKLIST:
- Task filenames are exactly: pom.xml; src/main/java/User.java; src/main/java/AuditEvent.java; src/main/java/UserValidator.java; src/main/java/SearchService.java; src/main/java/AuditLogService.java; src/main/java/UserRepository.java; src/main/java/InMemoryUserRepository.java; src/main/java/Main.java; src/test/java/MainTest.java.
- UserRepository.java literally begins with `import java.util.List;` before `public interface UserRepository`; every source that uses a java.util type imports that type directly and never relies on transitive imports.
- Main.java contains no collection type declaration or result variable and literally uses the standalone call `searchService.search(repository.findAll(), "alice");`; Main.java never spells `List`, `ArrayList`, or `Map` and needs no java.util import.
- User and AuditEvent are ordinary `public final class` declarations with private final fields and getters. Java record syntax is forbidden under Java 11; never emit `public record User` or `public record AuditEvent`.
- User stores constructor arguments unchanged and UserValidator alone checks null/blank fields; the repository validates on save. Search is exact case-insensitive whitespace-delimited name-token matching with the Alice Smith/Bob Jones fixture. Audit is explicit and never coupled to repository operations; tests log the two fixed events themselves. MainTest contains exactly three `@Test` methods using the three fixed scopes and no invented semantics.
- Logic Analysis and implementation tasks must preserve these class declarations and exact contracts and must not call either entity a Java record.
"""
    elif unit["unit_id"] == "p11_custom_press_releases_python":
        priority_footer = """

FINAL NON-NEGOTIABLE PRESS-RELEASE PYTHON 3.10 CHECKLIST:
- Task filenames are exactly: requirements.txt; press_releases/errors.py; press_releases/types.py; press_releases/template.py; press_releases/validation.py; press_releases/press_release.py; press_releases/search.py; press_releases/__init__.py; Main.py; tests/test_main.py. clock.py, datetime, lifecycle.py, history.py, and rendering.py are forbidden.
- PressRelease is an ordinary mutable class with no dataclass decorator and assigns normal attributes in its constructor. Only Contact, VersionEntry, and Template are frozen dataclasses, and they use generated initializers with no custom __init__. VersionEntry uses an integer number and rendered_text, never a timestamp.
- Template.render iterates exactly `for key in sorted(values)` and replaces `"{{" + key + "}}"`; result.split("{{"), part[2:-2], and regex parsing are forbidden. PressRelease construction never validates; invalid candidates are constructed, validate returns false, and submit_for_review raises DomainError.
- Main uses absolute press_releases imports. Tests use a separate literal `from Main import run_demo` line, import all domain symbols from press_releases, and never import run_demo from press_releases; press_releases/__init__.py never exports run_demo. Tests contain exactly three cases with the exact basic template, Alice contact, Hello/Body rendering, DRAFT/REVIEW/PUBLISHED lifecycle, version 1, explicit invalid-candidate validate/submit semantics, media/news tag, and search fixtures. The valid-DRAFT error assertion immediately calls publish inside `with pytest.raises(InvalidTransitionError)` before any submit_for_review on that object. Do not summarize or substitute these requirements.
"""
    elif unit["unit_id"] == "p11_custom_press_releases_java":
        priority_footer = """

FINAL NON-NEGOTIABLE PRESS-RELEASE JAVA 11 TYPE CHECKLIST:
- Task filenames are exactly: pom.xml; src/main/java/ReleaseState.java; src/main/java/Version.java; src/main/java/Template.java; src/main/java/Validator.java; src/main/java/PressRelease.java; src/main/java/TaggingSystem.java; src/main/java/RenderService.java; src/main/java/Main.java; src/test/java/MainTest.java.
- ReleaseState.java solely defines public enum ReleaseState with DRAFT, REVIEW, PUBLISHED; Version.java solely defines ordinary public final class Version with number/renderedText. They are never omitted or nested. Java record syntax and post-Java-11 syntax are forbidden.
- MainTest has exactly three @Test methods and preserves the exact basic template, validator, r1 lifecycle, media tag, version number 1, and rendered `Hello|Body|a@b.com` fixtures. No clock or implicit type is allowed.
"""
    elif unit["unit_id"] == "p12_video_player_java":
        priority_footer = """

FINAL NON-NEGOTIABLE VIDEO-PLAYER JAVA 11 STATE CHECKLIST:
- Task filenames are exactly pom.xml; MediaItem.java; Playlist.java; PlayerState.java; VolumeControl.java; DeterministicClock.java; PlayerSnapshot.java; PlaybackController.java; Main.java; MainTest.java at their standard Maven paths, all in the default package.
- PlayerState() literally initializes currentIndex=0, positionMillis=0, STOPPED; -1 is forbidden. VolumeControl.setVolume always updates both volume and lastNonMuted even while muted, so setting 30 while muted restores 30 on unmute. PlaybackController.play therefore succeeds for a nonempty new playlist at index 0.
- MainTest contains exactly three @Test methods with exact 5000ms end-of-media, 3000/4000 navigation/clamping, and 70->mute->30->unmute fixtures. Repeat these literal values and rules in Full API, Logic Analysis, Test Scope Plan, Shared Knowledge, and each affected task.
"""
    elif unit["unit_id"] == "p12_video_player_cpp":
        priority_footer = """

FINAL NON-NEGOTIABLE VIDEO-PLAYER C++ COMPILATION CHECKLIST:
- Task filenames are exactly: CMakeLists.txt; include/Time/IClock.h; include/Time/ManualClock.h; include/Time/MonotonicClock.h; include/Media/MediaMetadata.h; include/Playlist/Playlist.h; include/Player/PlaybackState.h; include/Player/Player.h; include/Runtime/App.h; src/Time/ManualClock.cpp; src/Time/MonotonicClock.cpp; src/Media/MediaMetadata.cpp; src/Playlist/Playlist.cpp; src/Player/Player.cpp; src/Runtime/App.cpp; src/Main.cpp; tests/test_main.cpp.
- IClock.h directly contains `#include <cstdint>` and declares `virtual std::int64_t now_ms() const noexcept = 0;`. Every header that names a signed 64-bit integer directly includes `<cstdint>`, every such type is spelled `std::int64_t`, and bare `int64_t` is forbidden.
- tests/test_main.cpp contains exactly one self-contained `int main()` and uses no GoogleTest or other test framework. CMake directly builds and registers video_player_tests without find_package, FetchContent, GTest, gtest, or any network dependency.
- src/Main.cpp only returns Runtime::App().run_demo() and never streams PlaybackState or another enum.
- Base/derived and header/source signatures use identical const and noexcept qualifiers. Do not summarize or omit these literal compilation tokens from Full API, Shared Knowledge, or affected implementation tasks.
"""
    elif unit["unit_id"] == "p13_video_downloader_cpp":
        priority_footer = """

FINAL NON-NEGOTIABLE VIDEO-DOWNLOADER C++17 CHECKLIST:
- Task filenames are exactly: CMakeLists.txt; include/DownloadTypes.h; include/Url.h; src/Url.cpp; include/SafeNamer.h; src/SafeNamer.cpp; include/Transfer.h; src/Transfer.cpp; include/DownloadQueue.h; src/DownloadQueue.cpp; src/Main.cpp; tests/test_main.cpp. Format.h, TransferAdapter.h, FakeTransfer.h, ExistingFiles.h, and InMemoryExistingFiles.h are forbidden.
- DownloadTypes.h solely owns and defines Format before DownloadItem. SafeNamer.h fully defines IExistingFiles before any caller invokes exists; no incomplete-type call is allowed. Transfer.h defines only the total_bytes adapter boundary, has no TransferSession and no bytesTransferred accessor. DownloadQueue alone mutates item.progress.bytes directly by min(chunk_size,total-bytes).
- DownloadQueue.cpp directly includes "Url.h" before calling is_valid_url/parse_format/extension_for; SafeNamer.cpp directly includes <utility> before std::move. URL host parsing begins after ://, so https:// and http:///path are invalid while https://example.com/clip is valid.
- SafeNamer.h defines a separate zero-argument InMemoryExistingFiles constructor and a vector constructor with no default argument. Empty objects are declared exactly `InMemoryExistingFiles files;`; `InMemoryExistingFiles files({});` is forbidden. Host-only https://example.com is valid and tests must not reject it.
- Every header is self-contained with its specified direct includes. CMake builds downloader_core/downloader_app/downloader_tests and registers the test without external packages. tests/test_main.cpp contains exactly one int main and four independent deterministic blocks for URL/format including the empty-host cases, clip_2.mp4 safe naming, 0/4/8/12 progress completion, and cancellation freeze. Repeat these literal ownership/API/fixture constraints in Full API, Logic Analysis, Shared Knowledge, C++ Build Link Audit, and affected tasks.
"""
    elif unit["unit_id"] == "p13_video_downloader_python":
        priority_footer = """

FINAL NON-NEGOTIABLE VIDEO-DOWNLOADER PYTHON 3.10 CHECKLIST:
- Task filenames are exactly requirements.txt; video_downloader/errors.py; url.py; naming.py; request.py; progress.py; transfer.py; queue.py; __init__.py; Main.py; tests/test_main.py at the specified paths.
- DownloadQueue is synchronous. Its deterministic cancellation test cancels the first pending job before process_all, expects 0/12 cancelled, and lets the second job complete at 8/8 with final_name b.mp4. A test requiring external mid-transfer cancellation is forbidden because process_next has no concurrent callback API.
- Tests contain exactly four cases with run_demo completed 12/12, InvalidURLError/InvalidFormatError, exact my_clip and clip (1).mp4 naming, and the exact two-job pre-start cancellation fixture. Repeat these literal rules in Full API, Logic Analysis, Test Scope Plan, Shared Knowledge, and affected tasks.
"""
    elif unit["unit_id"] == "p14_todo_list_app_java":
        priority_footer = """

FINAL NON-NEGOTIABLE TO-DO JAVA 11 COMPILATION CHECKLIST:
- Task filenames are exactly: pom.xml; src/main/java/Priority.java; src/main/java/Task.java; src/main/java/TaskRepository.java; src/main/java/InMemoryTaskRepository.java; src/main/java/TaskFilter.java; src/main/java/TaskSorter.java; src/main/java/TodoService.java; src/main/java/Main.java; src/test/java/MainTest.java. All use the default package. TaskDraft, TaskUpdate, TaskQuery, TaskSort, ValidationException, TimeProvider, TaskSummary, and ToDoService are forbidden.
- Java records, builders, Optional, streams, Stream.toList(), custom clocks, Comparator.comparing/thenComparing/reversed, Collections.reverseOrder, and compound comparator APIs are forbidden. Every affected file must include every literal import line from the project contract. TaskSorter uses one direct comparator with Integer.compare, LocalDate.compareTo, and String.CASE_INSENSITIVE_ORDER.compare. TaskFilter owns normalizeRequiredTags and never calls Task.normalizeTags.
- Task mutable values are not final. TaskRepository.findById returns Task or null. createTask literally constructs with nextId, saves, then executes `nextId += 1;`; `nextId++` and consuming an id on failed validation are forbidden. TodoService signatures, the exact total/completed/pending/overdue summary, fixed 2023-10-15 demo, and exactly four deterministic tests must be repeated without aliases or invented overloads in Full API, Logic Analysis, Test Scope Plan, Shared Knowledge, and affected tasks.
"""
    elif unit["unit_id"] == "p14_todo_list_app_python":
        priority_footer = """

FINAL NON-NEGOTIABLE TO-DO PYTHON 3.10 ERROR CHECKLIST:
- Task filenames are exactly requirements.txt; todo_app/errors.py; priority.py; entities.py; filtering.py; sorting.py; repository.py; clock.py; service.py; __init__.py; Main.py; tests/test_main.py at the specified paths.
- priority.py directly imports ValidationError from .errors, declares Priority with Enum rather than IntEnum, accepts Priority or low/med/medium/high strings, and raises only ValidationError for every invalid value. ValueError/TypeError/KeyError are forbidden outcomes. service.create_task propagates that ValidationError.
- Tests contain exactly four cases and specifically require ValidationError for priority="invalid", id-stable due-date sorting, completion idempotence, fixed-date summary, and public imports. Repeat these literal rules in Full API, Logic Analysis, Test Scope Plan, Shared Knowledge, and affected tasks.
"""
    elif unit["unit_id"] == "p14_todo_list_app_cpp":
        priority_footer = """

FINAL NON-NEGOTIABLE TO-DO C++17 COMPILATION CHECKLIST:
- Task filenames are exactly: CMakeLists.txt; include/Task.h; src/Task.cpp; include/Date.h; src/Date.cpp; include/Query.h; src/Query.cpp; include/TaskStore.h; src/TaskStore.cpp; include/TaskManager.h; src/TaskManager.cpp; src/Main.cpp; tests/test_main.cpp.
- TaskStore.h directly contains `#include <map>` before declaring `std::map<std::uint64_t, Task> tasks_`; Query.cpp directly contains `#include <set>` before using std::set. Every header and source contains all of its own standard-library includes and never relies on transitive includes.
- Query.h declares the global `enum class SortOrder { ByDueThenPriority, ByTitle };` outside and before class Query. Query::SortOrder and every nested SortOrder declaration are forbidden; TaskManager uses the unqualified global SortOrder type.
- Date.cpp declares every helper before first use, especially IsLeapYear before IsValidDay calls it. Empty dates sort after valid dates: compare_dates("",valid)>0 and compare_dates(valid,"")<0.
- CMake builds and links todo_core, todo_app, and todo_tests without an external framework. tests/test_main.cpp contains exactly one int main and exactly three deterministic independently scoped blocks; no block references a local id from another block. The invalid-data block creates and uses its own local existing_id. It must never put `std::vector<std::string>{"a", "b"}` directly inside an assert macro; first declare a named expected vector and compare against that name. Do not summarize or omit the literal <map>/<set>/helper-order/local-existing-id/assert-safety tokens from Full API, Logic Analysis, Shared Knowledge, or affected tasks.
"""
    return f"""Generate a complete medium-size {facts['display']} repository architecture for: {unit['task_name']}.

This architecture will be implemented later by a seeded local code model and evaluated automatically. Produce concrete design and implementation tasks for every file; do not use placeholders.

Normative evaluator protocol (these paths are mandatory and override preferences):
- build file: {facts['build_file']}
- runtime entry: {facts['runtime_entry']}
- single test target: {facts['test_target']}
- test command: {facts['test_command']}
- keep exactly one protocol-level test file; additional non-test implementation files are allowed

Language/layout constraints:
{facts['layout']}{unit_specific_constraints}

Medium-size reference from MetaProjectDev (descriptive only; the architecture model's generated file count is authoritative):
- about {targets['files']} repository files
- about {targets['functions']} functions or methods
- about {targets['loc']} lines of code

Sizing guidance:
- #Files, #Functions, and #LOC above are paper-table references, not acceptance bounds
- use the number of files produced by this architecture run; do not add or remove files merely to hit the reference
- count build, runtime, test, package markers, headers, and implementation files when reporting the realized size

Required domain behavior:
{features}

Cross-cutting requirements:
- separate pure domain logic from runtime, UI, filesystem, network, clock, and randomness boundaries
- automated tests must be deterministic, headless, offline, and require no manual interaction
- keep the single test target concise (2 to 4 tests, preferably under 150 LOC): cover runtime wiring and representative core rules, not the full feature matrix
- do not inflate the function/LOC target with test code; put substantive behavior in implementation files
- make every planned file small enough for one 4096-token code completion: prefer under 150 LOC and never plan a file over 220 LOC
- order the Task list strictly by implementation dependency: foundational types and interfaces first, then dependent implementations, then the runtime entry, and the single test target LAST (the build descriptor may be first)
- the Engineer code_todos must preserve that dependency-first Task-list order so later files can see already-generated dependency code
- the runtime entry must provide a small non-interactive demonstration that exits successfully or starts safely without an output loop
- validate invalid inputs and boundary cases
- keep public interfaces coherent across design, task list, implementation, and tests
- specify one canonical public API; tests must use it without inventing alternate semantics
- make Full API spec non-empty and exhaustive: for every public type/function give its exact module, signature, return value, error behavior, and key semantics; repeat these exact contracts in each affected file task
- tests may import only the canonical public API and should assert stable externally visible behavior, not private implementation details, incidental formatting, or unplanned aliases
- avoid circular dependencies; explicitly give the allowed import/include direction and ensure every referenced symbol is defined before a dependent file is generated
- avoid network access and OS-specific behavior during build, tests, and runtime checks
- all planned source, header, build, and test files must be listed exactly and consistently in the design and task documents
{priority_footer}
"""


SENSITIVE_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "password",
    "secret",
    "access_token",
    "refresh_token",
)


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: Dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(fragment in normalized for fragment in SENSITIVE_KEY_FRAGMENTS):
                redacted[key] = "***REDACTED***"
            else:
                redacted[key] = redact_secrets(item)
        return redacted
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    return value


def sanitize_team_json(path: Path) -> None:
    team = load_json(path)
    atomic_json(path, redact_secrets(team))


def canonicalize_generated_task_paths(unit: Dict[str, Any], value: Any) -> Any:
    """Normalize bare protocol filenames while retaining the raw model task.

    Local planners sometimes preserve the right Java class set but drop the
    Maven source roots from every task field. The evaluator path is normative,
    so repair only unqualified ``*.java`` references; already-qualified paths
    and all semantic content remain unchanged.
    """
    if isinstance(value, dict):
        return {
            key: canonicalize_generated_task_paths(unit, item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [canonicalize_generated_task_paths(unit, item) for item in value]
    if not isinstance(value, str) or unit["language"] != "java":
        return value

    def replace_java_filename(match: re.Match[str]) -> str:
        filename = match.group(1)
        root = "src/test/java" if filename == "MainTest.java" else "src/main/java"
        return "{}/{}".format(root, filename)

    return re.sub(
        r"(?<![/A-Za-z0-9_.-])([A-Z][A-Za-z0-9_]*\.java)(?![A-Za-z0-9_.-])",
        replace_java_filename,
        value,
    )


def code_todo_filenames(team_path: Path) -> List[str]:
    team = load_json(team_path)
    roles = ((team.get("env") or {}).get("roles") or {})
    engineer: Dict[str, Any] = {}
    for name, role in roles.items():
        if str(name).lower() == "engineer" or str(role.get("profile", "")).lower() == "engineer":
            engineer = role
            break
    filenames: List[str] = []
    for todo in engineer.get("code_todos") or []:
        context = todo.get("i_context") or {}
        raw = context.get("content") or "{}"
        try:
            coding_context = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            coding_context = {}
        filename = coding_context.get("filename") or context.get("filename")
        if filename:
            filenames.append(str(filename))
    return filenames


def unit_architecture_contract_issues(
    unit: Dict[str, Any], filenames: Sequence[str], repo_path: Path
) -> List[str]:
    """Reject per-unit design drift before any seed is spent on it."""
    required_by_unit = {
        "p06_tank_battle_game_java": {
            "pom.xml",
            "src/main/java/Position.java",
            "src/main/java/Orientation.java",
            "src/main/java/Command.java",
            "src/main/java/Tank.java",
            "src/main/java/Projectile.java",
            "src/main/java/ObstacleMap.java",
            "src/main/java/Arena.java",
            "src/main/java/ScoreBoard.java",
            "src/main/java/GameEngine.java",
            "src/main/java/Main.java",
            "src/test/java/MainTest.java",
        },
        "p04_caro_game_java": {
            "pom.xml",
            "src/main/java/Player.java",
            "src/main/java/Move.java",
            "src/main/java/Board.java",
            "src/main/java/GameState.java",
            "src/main/java/WinDetector.java",
            "src/main/java/Game.java",
            "src/main/java/Main.java",
            "src/test/java/MainTest.java",
        },
        "p05_brick_breaker_game_python": {
            "requirements.txt",
            "brick_breaker/config.py",
            "brick_breaker/ball.py",
            "brick_breaker/paddle.py",
            "brick_breaker/brick.py",
            "brick_breaker/level.py",
            "brick_breaker/collision.py",
            "brick_breaker/game.py",
            "brick_breaker/__init__.py",
            "Main.py",
            "tests/test_main.py",
        },
        "p06_tank_battle_game_python": {
            "requirements.txt",
            "tank_battle/__init__.py",
            "tank_battle/geometry.py",
            "tank_battle/directions.py",
            "tank_battle/obstacle.py",
            "tank_battle/arena.py",
            "tank_battle/tank.py",
            "tank_battle/projectile.py",
            "tank_battle/commands.py",
            "tank_battle/scoring.py",
            "tank_battle/game.py",
            "tank_battle/configs.py",
            "Main.py",
            "tests/test_main.py",
        },
        "p07_calculator_python": {
            "requirements.txt",
            "calculator/errors.py",
            "calculator/history.py",
            "calculator/tokenizer.py",
            "calculator/engine.py",
            "calculator/api.py",
            "calculator/__init__.py",
            "Main.py",
            "tests/test_main.py",
        },
        "p08_excel_data_processing_python": {
            "requirements.txt",
            "excel_processor/model.py",
            "excel_processor/operations.py",
            "excel_processor/csv_io.py",
            "excel_processor/report.py",
            "excel_processor/__init__.py",
            "Main.py",
            "tests/test_main.py",
        },
        "p09_qr_code_gen_det_cpp": {
            "CMakeLists.txt",
            "include/QRMatrix.h",
            "src/QRMatrix.cpp",
            "include/QRCodec.h",
            "src/QRCodec.cpp",
            "include/QRRenderer.h",
            "src/QRRenderer.cpp",
            "src/Main.cpp",
            "tests/test_main.cpp",
        },
        "p09_qr_code_gen_det_python": {
            "requirements.txt",
            "qr_code/payload.py",
            "qr_code/matrix.py",
            "qr_code/codec.py",
            "qr_code/render.py",
            "qr_code/__init__.py",
            "Main.py",
            "tests/test_main.py",
        },
        "p09_qr_code_gen_det_java": {
            "pom.xml",
            "src/main/java/QRMatrix.java",
            "src/main/java/Checksum.java",
            "src/main/java/ZigZag.java",
            "src/main/java/FinderPattern.java",
            "src/main/java/TextEncoder.java",
            "src/main/java/MatrixValidator.java",
            "src/main/java/QRDetector.java",
            "src/main/java/QRCodec.java",
            "src/main/java/QRRenderer.java",
            "src/main/java/Main.java",
            "src/test/java/MainTest.java",
        },
        "p10_crud_system_cpp": {
            "CMakeLists.txt",
            "include/Record.h",
            "src/Record.cpp",
            "include/ManualClock.h",
            "src/ManualClock.cpp",
            "include/Repository.h",
            "src/Repository.cpp",
            "include/CrudService.h",
            "src/CrudService.cpp",
            "src/Main.cpp",
            "tests/test_main.cpp",
        },
        "p10_crud_system_python": {
            "requirements.txt",
            "crud_system/errors.py",
            "crud_system/types.py",
            "crud_system/clock.py",
            "crud_system/validation.py",
            "crud_system/repository.py",
            "crud_system/search.py",
            "crud_system/audit.py",
            "crud_system/service.py",
            "crud_system/__init__.py",
            "Main.py",
            "tests/test_main.py",
        },
        "p10_crud_system_java": {
            "pom.xml",
            "src/main/java/User.java",
            "src/main/java/AuditEvent.java",
            "src/main/java/UserValidator.java",
            "src/main/java/SearchService.java",
            "src/main/java/AuditLogService.java",
            "src/main/java/UserRepository.java",
            "src/main/java/InMemoryUserRepository.java",
            "src/main/java/Main.java",
            "src/test/java/MainTest.java",
        },
        "p11_custom_press_releases_python": {
            "requirements.txt",
            "press_releases/errors.py",
            "press_releases/types.py",
            "press_releases/template.py",
            "press_releases/validation.py",
            "press_releases/press_release.py",
            "press_releases/search.py",
            "press_releases/__init__.py",
            "Main.py",
            "tests/test_main.py",
        },
        "p11_custom_press_releases_java": {
            "pom.xml",
            "src/main/java/ReleaseState.java",
            "src/main/java/Version.java",
            "src/main/java/Template.java",
            "src/main/java/Validator.java",
            "src/main/java/PressRelease.java",
            "src/main/java/TaggingSystem.java",
            "src/main/java/RenderService.java",
            "src/main/java/Main.java",
            "src/test/java/MainTest.java",
        },
        "p12_video_player_java": {
            "pom.xml",
            "src/main/java/MediaItem.java",
            "src/main/java/Playlist.java",
            "src/main/java/PlayerState.java",
            "src/main/java/VolumeControl.java",
            "src/main/java/DeterministicClock.java",
            "src/main/java/PlayerSnapshot.java",
            "src/main/java/PlaybackController.java",
            "src/main/java/Main.java",
            "src/test/java/MainTest.java",
        },
        "p12_video_player_cpp": {
            "CMakeLists.txt",
            "include/Time/IClock.h",
            "include/Time/ManualClock.h",
            "include/Time/MonotonicClock.h",
            "include/Media/MediaMetadata.h",
            "include/Playlist/Playlist.h",
            "include/Player/PlaybackState.h",
            "include/Player/Player.h",
            "include/Runtime/App.h",
            "src/Time/ManualClock.cpp",
            "src/Time/MonotonicClock.cpp",
            "src/Media/MediaMetadata.cpp",
            "src/Playlist/Playlist.cpp",
            "src/Player/Player.cpp",
            "src/Runtime/App.cpp",
            "src/Main.cpp",
            "tests/test_main.cpp",
        },
        "p13_video_downloader_cpp": {
            "CMakeLists.txt",
            "include/DownloadTypes.h",
            "include/Url.h",
            "src/Url.cpp",
            "include/SafeNamer.h",
            "src/SafeNamer.cpp",
            "include/Transfer.h",
            "src/Transfer.cpp",
            "include/DownloadQueue.h",
            "src/DownloadQueue.cpp",
            "src/Main.cpp",
            "tests/test_main.cpp",
        },
        "p13_video_downloader_python": {
            "requirements.txt",
            "video_downloader/errors.py",
            "video_downloader/url.py",
            "video_downloader/naming.py",
            "video_downloader/request.py",
            "video_downloader/progress.py",
            "video_downloader/transfer.py",
            "video_downloader/queue.py",
            "video_downloader/__init__.py",
            "Main.py",
            "tests/test_main.py",
        },
        "p14_todo_list_app_java": {
            "pom.xml",
            "src/main/java/Priority.java",
            "src/main/java/Task.java",
            "src/main/java/TaskRepository.java",
            "src/main/java/InMemoryTaskRepository.java",
            "src/main/java/TaskFilter.java",
            "src/main/java/TaskSorter.java",
            "src/main/java/TodoService.java",
            "src/main/java/Main.java",
            "src/test/java/MainTest.java",
        },
        "p14_todo_list_app_python": {
            "requirements.txt",
            "todo_app/errors.py",
            "todo_app/priority.py",
            "todo_app/entities.py",
            "todo_app/filtering.py",
            "todo_app/sorting.py",
            "todo_app/repository.py",
            "todo_app/clock.py",
            "todo_app/service.py",
            "todo_app/__init__.py",
            "Main.py",
            "tests/test_main.py",
        },
        "p14_todo_list_app_cpp": {
            "CMakeLists.txt",
            "include/Task.h",
            "src/Task.cpp",
            "include/Date.h",
            "src/Date.cpp",
            "include/Query.h",
            "src/Query.cpp",
            "include/TaskStore.h",
            "src/TaskStore.cpp",
            "include/TaskManager.h",
            "src/TaskManager.cpp",
            "src/Main.cpp",
            "tests/test_main.cpp",
        },
    }
    forbidden_by_unit = {
        "p06_tank_battle_game_python": {
            "tank_battle/direction.py",
            "tank_battle/demo.py",
            "tank_battle/entities.py",
            "tank_battle/scoreboard.py",
        },
        "p08_excel_data_processing_python": {
            "excel_processor/cell.py",
            "excel_processor/row.py",
            "excel_processor/sheet.py",
            "excel_processor/filter.py",
            "excel_processor/sort.py",
            "excel_processor/csv_utils.py",
        },
        "p14_todo_list_app_java": {
            "src/main/java/TaskDraft.java",
            "src/main/java/TaskUpdate.java",
            "src/main/java/TaskQuery.java",
            "src/main/java/TaskSort.java",
            "src/main/java/ValidationException.java",
            "src/main/java/TimeProvider.java",
            "src/main/java/TaskSummary.java",
            "src/main/java/ToDoService.java",
        },
    }
    planned = set(filenames)
    issues: List[str] = []
    missing = sorted(required_by_unit.get(unit["unit_id"], set()) - planned)
    if missing:
        issues.append("missing project-contract files: {}".format(", ".join(missing)))
    if unit["unit_id"] in {
        "p05_brick_breaker_game_python",
        "p06_tank_battle_game_java",
        "p06_tank_battle_game_python",
        "p07_calculator_python",
        "p08_excel_data_processing_python",
        "p09_qr_code_gen_det_cpp",
        "p09_qr_code_gen_det_java",
        "p09_qr_code_gen_det_python",
        "p10_crud_system_cpp",
        "p10_crud_system_python",
        "p10_crud_system_java",
        "p11_custom_press_releases_python",
        "p11_custom_press_releases_java",
        "p12_video_player_java",
        "p12_video_player_cpp",
        "p13_video_downloader_cpp",
        "p13_video_downloader_python",
        "p14_todo_list_app_java",
        "p14_todo_list_app_python",
        "p14_todo_list_app_cpp",
    }:
        unexpected = sorted(planned - required_by_unit[unit["unit_id"]])
        if unexpected:
            issues.append(
                "unexpected project-contract files: {}".format(", ".join(unexpected))
            )
    forbidden = sorted(forbidden_by_unit.get(unit["unit_id"], set()) & planned)
    if forbidden:
        issues.append("forbidden project-contract aliases: {}".format(", ".join(forbidden)))
    if unit["unit_id"] == "p04_caro_game_java":
        task_dir = repo_path / "docs" / "task"
        task_docs = sorted(task_dir.glob("*.json")) if task_dir.exists() else []
        task_parts: List[str] = []
        for task_path in task_docs:
            try:
                task_parts.append(
                    json.dumps(load_json(task_path), ensure_ascii=False, sort_keys=True)
                )
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
        normalized_task = "".join(" ".join(task_parts).split()).lower()
        required_task_fragments = {
            "exact nine-move alternating fixture": (
                "(7,3),(0,0),(7,4),(0,2),(7,5),(0,4),(7,6),(0,6),(7,7)"
            ),
            "exactly-three-test limit": "exactlythree",
            "first state-fixture move": "placemove(1,1)",
            "second state-fixture move": "placemove(2,2)",
        }
        if not normalized_task:
            issues.append("missing project-contract task specification")
        for label, fragment in required_task_fragments.items():
            if fragment not in normalized_task:
                issues.append("task specification missing {} ({})".format(label, fragment))
        if "nineconsecutivemovesbyx" in normalized_task:
            issues.append("task specification contains forbidden consecutive-X fixture")
    if unit["unit_id"] == "p05_brick_breaker_game_cpp":
        task_dir = repo_path / "docs" / "task"
        task_docs = sorted(task_dir.glob("*.json")) if task_dir.exists() else []
        task_parts: List[str] = []
        for task_path in task_docs:
            try:
                task_parts.append(str(load_json(task_path).get("Full API spec", "")))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
        normalized_task = "".join(" ".join(task_parts).split()).lower()
        required_task_fragments = {
            "direct cstddef include": "#include<cstddef>",
            "qualified size type": "std::size_t",
            "direct Collision include": '#include"collision.h"',
            "direct cmath include": "#include<cmath>",
            "qualified square root": "std::sqrt",
        }
        if not normalized_task:
            issues.append("missing project-contract task specification")
        for label, fragment in required_task_fragments.items():
            if fragment not in normalized_task:
                issues.append("task specification missing {} ({})".format(label, fragment))
    if unit["unit_id"] == "p05_brick_breaker_game_python":
        task_dir = repo_path / "docs" / "task"
        task_docs = sorted(task_dir.glob("*.json")) if task_dir.exists() else []
        full_api_parts: List[str] = []
        for task_path in task_docs:
            try:
                full_api_parts.append(str(load_json(task_path).get("Full API spec", "")))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
        normalized_api = "".join(" ".join(full_api_parts).split()).lower()
        required_api_fragments = {
            "config module": "brick_breaker/config.py",
            "GameConfig declaration": "classgameconfig",
            "direct config import": "from.configimportgameconfig",
        }
        if not normalized_api:
            issues.append("missing project-contract Full API specification")
        for label, fragment in required_api_fragments.items():
            if fragment not in normalized_api:
                issues.append(
                    "Full API missing {} ({})".format(label, fragment)
                )
    if unit["unit_id"] == "p07_calculator_python":
        task_dir = repo_path / "docs" / "task"
        task_docs = sorted(task_dir.glob("*.json")) if task_dir.exists() else []
        full_api_parts: List[str] = []
        test_scope_entries: List[Any] = []
        for task_path in task_docs:
            try:
                task_data = load_json(task_path)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
            full_api_parts.append(str(task_data.get("Full API spec", "")))
            test_scope = task_data.get("Test Scope Plan", [])
            if isinstance(test_scope, list):
                test_scope_entries.extend(test_scope)
        normalized_api = "".join(" ".join(full_api_parts).split()).lower()
        required_api_fragments = {
            "sole tokenizer error import": "from.errorsimporttokenizationerror",
            "forbidden relative tokenizer self-import": "from.tokenizerimport",
            "forbidden absolute tokenizer self-import": "fromcalculator.tokenizerimport",
            "Token class declaration": "classtoken:",
            "forbidden Token object alias": "token=object",
            "engine token import": (
                "from.tokenizerimporttoken,numbertoken,optoken,lparentoken,rparentoken"
            ),
            "public token count fixture": 'len(tokenize("1+2.5"))==3',
            "forbidden reflective token constructor": "type(tokens[0])()",
            "three-test limit": "exactlythree",
        }
        if not normalized_api:
            issues.append("missing project-contract Full API specification")
        for label, fragment in required_api_fragments.items():
            if fragment not in normalized_api:
                issues.append("Full API missing {} ({})".format(label, fragment))
        normalized_scope = "".join(" ".join(map(str, test_scope_entries)).split()).lower()
        if len(test_scope_entries) != 3:
            issues.append(
                "Test Scope Plan must contain exactly three rows (found {})".format(
                    len(test_scope_entries)
                )
            )
        for label, fragment in {
            "runtime/arithmetic fixture": "2+3*4",
            "history fixture": "(1+2)*3",
            "token-count fixture": "1+2.5",
            "domain-error fixture": "evaluationerror",
        }.items():
            if fragment not in normalized_scope:
                issues.append("Test Scope Plan missing {} ({})".format(label, fragment))
    if unit["unit_id"] == "p08_excel_data_processing_java":
        task_dir = repo_path / "docs" / "task"
        task_docs = sorted(task_dir.glob("*.json")) if task_dir.exists() else []
        full_api_parts: List[str] = []
        test_scope_entries: List[Any] = []
        for task_path in task_docs:
            try:
                task_data = load_json(task_path)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
            full_api_parts.append(str(task_data.get("Full API spec", "")))
            test_scope = task_data.get("Test Scope Plan", [])
            if isinstance(test_scope, list):
                test_scope_entries.extend(test_scope)
        normalized_api = "".join(" ".join(full_api_parts).split()).lower()
        required_api_fragments = {
            "Java 11 stream ban": "stream.tolist()",
            "report-taking import": (
                "sheetimportcsvfromstring(stringname,stringcsv,processingreportreport)"
            ),
            "report-taking export": (
                "stringtocsvstring(sheetsheet,processingreportreport)"
            ),
            "rows-read ownership": "incrementrowsread",
            "rows-kept ownership": "incrementrowskept",
            "rows-written ownership": "incrementrowswritten",
            "default-package import ban": "importsheet",
            "pipeline fixture": "alice,us,1000",
            "filtered Row-to-Cell assertion": (
                "filteredrows.get(1).get(\"name\").raw()"
            ),
            "sorted Row-to-Cell assertion": (
                "sortedrows.get(0).get(\"name\").raw()"
            ),
            "invalid fixture": "bob,bad",
            "fresh report contract": "freshprocessingreport",
            "three-test limit": "exactlythree",
        }
        if not normalized_api:
            issues.append("missing project-contract Full API specification")
        for label, fragment in required_api_fragments.items():
            if fragment not in normalized_api:
                issues.append("Full API missing {} ({})".format(label, fragment))
        normalized_scope = "".join(" ".join(map(str, test_scope_entries)).split()).lower()
        if len(test_scope_entries) != 3:
            issues.append(
                "Test Scope Plan must contain exactly three rows (found {})".format(
                    len(test_scope_entries)
                )
            )
        for label, fragment in {
            "runtime fixture": "main.main",
            "pipeline fixture": "alice,us,1000",
            "invalid fixture": "bob,bad",
            "round-trip fixture": "rowswritten",
        }.items():
            if fragment not in normalized_scope:
                issues.append("Test Scope Plan missing {} ({})".format(label, fragment))
    if unit["unit_id"] == "p09_qr_code_gen_det_cpp":
        task_dir = repo_path / "docs" / "task"
        task_docs = sorted(task_dir.glob("*.json")) if task_dir.exists() else []
        full_api_parts: List[str] = []
        test_scope_entries: List[Any] = []
        for task_path in task_docs:
            try:
                task_data = load_json(task_path)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
            full_api_parts.append(str(task_data.get("Full API spec", "")))
            test_scope = task_data.get("Test Scope Plan", [])
            if isinstance(test_scope, list):
                test_scope_entries.extend(test_scope)
        normalized_api = "".join(" ".join(full_api_parts).split()).lower()
        required_api_fragments = {
            "fixed matrix size": "staticconstexprstd::size_tsize=21",
            "fixed finder size": "staticconstexprstd::size_tfinder_size=5",
            "row-major data capacity": "366",
            "matrix header self-containment": "<cstddef>",
            "codec direct project include": '"qrmatrix.h"',
            "wire length field": "length8",
            "literal finder corruption": "corrupted.set(0,0,false);",
            "three-scope limit": "exactlythree",
        }
        if not normalized_api:
            issues.append("missing project-contract Full API specification")
        for label, fragment in required_api_fragments.items():
            if fragment not in normalized_api:
                issues.append("Full API missing {} ({})".format(label, fragment))
        normalized_scope = "".join(
            " ".join(map(str, test_scope_entries)).split()
        ).lower()
        if len(test_scope_entries) != 3:
            issues.append(
                "Test Scope Plan must contain exactly three rows (found {})".format(
                    len(test_scope_entries)
                )
            )
        for label, fragment in {
            "UTF-8 round-trip fixture": "hello-\u4e16\u754c",
            "finder corruption fixture": "corrupted",
            "render fixture": "20",
            "oversize fixture": "41",
        }.items():
            if fragment not in normalized_scope:
                issues.append("Test Scope Plan missing {} ({})".format(label, fragment))
    if unit["unit_id"] == "p10_crud_system_cpp":
        task_dir = repo_path / "docs" / "task"
        task_docs = sorted(task_dir.glob("*.json")) if task_dir.exists() else []
        full_api_parts: List[str] = []
        test_scope_entries: List[Any] = []
        for task_path in task_docs:
            try:
                task_data = load_json(task_path)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
            full_api_parts.append(str(task_data.get("Full API spec", "")))
            test_scope = task_data.get("Test Scope Plan", [])
            if isinstance(test_scope, list):
                test_scope_entries.extend(test_scope)
        normalized_api = "".join(" ".join(full_api_parts).split()).lower()
        required_api_fragments = {
            "Record declaration": "structrecord",
            "revision field": "std::uint64_trevision",
            "timestamp field": "std::uint64_tupdated_at",
            "Repository direct Record include": '"record.h"',
            "concrete deterministic store": "std::map<std::string,record>",
            "service constructor dependencies": "crudservice(repository&,manualclock&)",
            "three-scope limit": "exactlythree",
        }
        if not normalized_api:
            issues.append("missing project-contract Full API specification")
        for label, fragment in required_api_fragments.items():
            if fragment not in normalized_api:
                issues.append("Full API missing {} ({})".format(label, fragment))
        normalized_scope = "".join(
            " ".join(map(str, test_scope_entries)).split()
        ).lower()
        if len(test_scope_entries) != 3:
            issues.append(
                "Test Scope Plan must contain exactly three rows (found {})".format(
                    len(test_scope_entries)
                )
            )
        for label, fragment in {
            "initial timestamp": "100",
            "updated timestamp": "105",
            "duplicate rejection": "duplicate",
            "deterministic order": "a",
        }.items():
            if fragment not in normalized_scope:
                issues.append("Test Scope Plan missing {} ({})".format(label, fragment))
    if unit["unit_id"] == "p10_crud_system_python":
        task_dir = repo_path / "docs" / "task"
        task_docs = sorted(task_dir.glob("*.json")) if task_dir.exists() else []
        full_api_parts: List[str] = []
        test_scope_entries: List[Any] = []
        for task_path in task_docs:
            try:
                task_data = load_json(task_path)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
            full_api_parts.append(str(task_data.get("Full API spec", "")))
            test_scope = task_data.get("Test Scope Plan", [])
            if isinstance(test_scope, list):
                test_scope_entries.extend(test_scope)
        normalized_api = "".join(" ".join(full_api_parts).split()).lower()
        required_api_fragments = {
            "non-generic Page declaration": "classpage:",
            "Page item field": "items:list[item]",
            "exact pagination return type": (
                "paginate(items:list[item],limit:int|none=none,offset:int=0)->page"
            ),
            "generic Page prohibition": "page[item]",
            "Python 3.10 import boundary": "python3.10",
            "direct repository error imports": (
                "from.errorsimportduplicatenameerror,notfounderror"
            ),
            "clock ownership": "soleclockconsumer",
            "single timestamp read": "clock.now()exactlyonce",
            "clock-free audit constructor": "audittrail()takesnoclock",
            "basic timestamp fixture": "createsat100.0andupdatesat110.0",
            "audit timestamp fixture": "[100.0,110.0,120.0]",
            "three-test limit": "exactlythree",
        }
        if not normalized_api:
            issues.append("missing project-contract Full API specification")
        for label, fragment in required_api_fragments.items():
            if fragment not in normalized_api:
                issues.append("Full API missing {} ({})".format(label, fragment))
        normalized_scope = "".join(
            " ".join(map(str, test_scope_entries)).split()
        ).lower()
        if len(test_scope_entries) != 3:
            issues.append(
                "Test Scope Plan must contain exactly three rows (found {})".format(
                    len(test_scope_entries)
                )
            )
        for label, fragment in {
            "basic CRUD fixture": "crud",
            "duplicate fixture": "duplicate",
            "pagination fixture": "pagination",
            "audit fixture": "audit",
        }.items():
            if fragment not in normalized_scope:
                issues.append("Test Scope Plan missing {} ({})".format(label, fragment))
    if unit["unit_id"] == "p09_qr_code_gen_det_java":
        task_dir = repo_path / "docs" / "task"
        task_docs = sorted(task_dir.glob("*.json")) if task_dir.exists() else []
        full_api_parts: List[str] = []
        test_scope_entries: List[Any] = []
        for task_path in task_docs:
            try:
                task_data = load_json(task_path)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
            full_api_parts.append(str(task_data.get("Full API spec", "")))
            test_scope = task_data.get("Test Scope Plan", [])
            if isinstance(test_scope, list):
                test_scope_entries.extend(test_scope)
        normalized_api = "".join(" ".join(full_api_parts).split()).lower()
        required_api_fragments = {
            "prefix-only checksum input": (
                "java.util.arrays.copyof(frame,frame.length-1)"
            ),
            "MSB-first byte expansion": (
                "bits[i*8+bit]=(bytes[i]&(1<<(7-bit)))!=0;"
            ),
            "ceil byte allocation": "byte[]result=newbyte[(bits.length+7)/8];",
            "MSB-first partial-byte write": (
                "result[i/8]|=(byte)(1<<(7-(i%8)));"
            ),
            "unreserved traversal allocation": "int[][]result=newint[count][2];",
            "bounded traversal row loop": "for(introw=0;row<size;row++)",
            "forbidden square traversal allocation": "newint[size*size][2]",
            "forbidden square traversal termination": "index<size*size",
            "length-derived frame size": "intframelength=2+length+1;",
            "length-derived frame copy": (
                "byte[]frame=java.util.arrays.copyof(bytes,framelength);"
            ),
            "non-byte-aligned input rule": "bits.length%8!=0",
            "nine-bit fixture": (
                "newboolean[]{true,false,false,false,false,false,false,false,true}"
            ),
            "round-trip fixture": "hello-\u4e16\u754c",
            "size-21 auto-size start": "intsize=21;",
            "default-package test import ban": "importqrcodec",
            "three-test limit": "exactlythree",
        }
        if not normalized_api:
            issues.append("missing project-contract Full API specification")
        for label, fragment in required_api_fragments.items():
            if fragment not in normalized_api:
                issues.append("Full API missing {} ({})".format(label, fragment))
        normalized_scope = "".join(" ".join(map(str, test_scope_entries)).split()).lower()
        if len(test_scope_entries) != 3:
            issues.append(
                "Test Scope Plan must contain exactly three rows (found {})".format(
                    len(test_scope_entries)
                )
            )
        for label, fragment in {
            "runtime fixture": "main.main",
            "padding fixture": "nine-bit",
            "round-trip fixture": "hello-\u4e16\u754c",
            "finder corruption fixture": "finder",
        }.items():
            if fragment not in normalized_scope:
                issues.append("Test Scope Plan missing {} ({})".format(label, fragment))
    if unit["unit_id"] == "p06_tank_battle_game_java":
        task_dir = repo_path / "docs" / "task"
        task_docs = sorted(task_dir.glob("*.json")) if task_dir.exists() else []
        full_api_parts: List[str] = []
        test_scope_entries: List[Any] = []
        for task_path in task_docs:
            try:
                task_data = load_json(task_path)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
            full_api_parts.append(str(task_data.get("Full API spec", "")))
            test_scope = task_data.get("Test Scope Plan", [])
            if isinstance(test_scope, list):
                test_scope_entries.extend(test_scope)
        normalized_api = "".join(" ".join(full_api_parts).split()).lower()
        required_api_fragments = {
            "mutable Tank position": "privatepositionposition;",
            "mutable Tank orientation": "privateorientationorientation;",
            "Projectile position mutator": "voidsetposition(positionposition)",
            "ScoreBoard reset API": "voidreset(collection<string>tankids)",
            "GameEngine reset boundary": "scoreboard.reset(initialtanks.keyset())",
            "mutable current Arena": "privatearenaarena;",
            "final initial Arena": "privatefinalarenainitialarena;",
            "mutable current Tank map": "privatemap<string,tank>tanks;",
            "initial Tank map": "privatefinalmap<string,tank>initialtanks;",
            "independent initial Tank copy": "tankinitialcopy=tank.copy();",
            "independent current Tank copy": "tankcurrentcopy=tank.copy();",
            "initial copy insertion": "this.initialtanks.put(tank.getid(),initialcopy);",
            "current copy insertion": "this.tanks.put(tank.getid(),currentcopy);",
            "current Arena reset": "this.arena=initialarena.copy();",
            "current Tank map reset": "this.tanks=newhashmap<>();",
            "preserved initial Tank snapshot": "mustneverbecleared",
            "no Collectors": "collectorsareforbidden",
            "qualified Arrays": "java.util.arrays.aslist",
            "dead Tank copy support": "copy()mustworkwhenhealthiszero",
            "zero-health constructor support": "permitshealth==0",
            "live initial Tank boundary": "initiallyalivetanks(health>0)",
            "same-tick spawn cell": "position(2,2)",
            "same-tick target cell": "position(3,2)",
            "three-test limit": "exactlythree",
            "fresh-copy rule": "fresh",
            "constructor-input observation ban": "mustneverinspect",
        }
        if not normalized_api:
            issues.append("missing project-contract Full API specification")
        for label, fragment in required_api_fragments.items():
            if fragment not in normalized_api:
                issues.append("Full API missing {} ({})".format(label, fragment))
        normalized_scope = "".join(" ".join(map(str, test_scope_entries)).split()).lower()
        if len(test_scope_entries) != 3:
            issues.append(
                "Test Scope Plan must contain exactly three rows (found {})".format(
                    len(test_scope_entries)
                )
            )
        for label, fragment in {
            "runtime fixture": "main.main",
            "blocked movement fixture": "blocked",
            "reset fixture": "reset",
            "hit/kill fixture": "hit",
            "score assertion": "score6",
            "fresh-copy assertion": "fresh",
        }.items():
            if fragment not in normalized_scope:
                issues.append("Test Scope Plan missing {} ({})".format(label, fragment))
    if unit["unit_id"] == "p06_tank_battle_game_python":
        task_dir = repo_path / "docs" / "task"
        task_docs = sorted(task_dir.glob("*.json")) if task_dir.exists() else []
        full_api_parts: List[str] = []
        test_scope_entries: List[Any] = []
        for task_path in task_docs:
            try:
                task_data = load_json(task_path)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
            full_api_parts.append(str(task_data.get("Full API spec", "")))
            test_scope = task_data.get("Test Scope Plan", [])
            if isinstance(test_scope, list):
                test_scope_entries.extend(test_scope)
        normalized_api = "".join(" ".join(full_api_parts).split()).lower()
        if not normalized_api:
            issues.append("missing project-contract Full API specification")
        required_api_fragments = {
            "string tank id": "id:str",
            "string projectile owner id": "owner_id:str",
            "tank dictionary": "tanks:dict[str,tank]",
            "string queue player id": "player_id:str",
            "demo returns Game": "build_default_demo()->game",
            "hit accounting method": "record_hit",
            "separate kill accounting": "record_kill",
            "score method": "score(",
            "ScoreBoard player-id constructor": "scoreboard(player_ids:list[str])",
            "Game initializes ScoreBoard from initial tanks": (
                "scoreboard(list(self._initial_tanks))",
                "scoreboard(list(self._initial_tanks.keys()))",
            ),
            "zeroed score dictionaries": '{"p1":0,"p2":0}',
            "direct command imports": (
                "from.commandsimportcommand,moveforward,rotateleft,rotateright,rotateto,fire",
                "fromtank_battle.commandsimportcommand,moveforward,rotateleft,rotateright,rotateto,fire",
            ),
            "marker Command without execute": "commandhasnoexecutemethod",
            "Game isinstance command dispatch": "game.tickdispatchessolelywithisinstance",
            "hit credited to projectile owner": "self.scores.record_hit(projectile.owner_id)",
            "kill credited to projectile owner": "self.scores.record_kill(projectile.owner_id)",
            "absolute package test import": "fromtank_battleimport",
            "absolute Main test import": "frommainimportrun_demo",
            "Main imports RotateRight": "fromtank_battleimportbuild_default_demo,rotateright",
            "Main queues command instance": 'game.queue_command("p1",rotateright())',
            "exact score formula": (
                "score(player_id)=hits+5*kills",
                "returnshits[player_id]+5*kills[player_id]",
                "returnshits.get(player_id,0)+5*kills.get(player_id,0)",
            ),
            "MoveForward positive-step validation": (
                "steps<1",
                "stepsmustbe>=1",
            ),
            "exact demo arena": (
                "arena(8,5,[])",
                "arena(width=8,height=5,obstacles=[])",
            ),
            "Enum import": "fromenumimportenum",
            "Direction Enum declaration": "classdirection(enum):",
            "north Enum value": "n=(0,-1)",
            "east Enum value": "e=(1,0)",
            "south Enum value": "s=(0,1)",
            "west Enum value": "w=(-1,0)",
            "reset captures pristine initial state": (
                "immediatelyrecords`initial=game.snapshot()`beforeanycommandortick",
                "immediatelyrecordsinitial=game.snapshot()beforeanycommandortick",
            ),
        }
        for label, fragment_or_options in required_api_fragments.items():
            options = (
                fragment_or_options
                if isinstance(fragment_or_options, tuple)
                else (fragment_or_options,)
            )
            if not any(fragment in normalized_api for fragment in options):
                issues.append(
                    "Full API missing {} ({})".format(label, " or ".join(options))
                )
        forbidden_api_fragments = {
            "numeric tank id": "fieldsid:int,name:str",
            "numeric projectile owner id": "owner_id:int",
            "numeric queue player id": "player_id:int",
            "tuple-returning demo": "build_default_demo()->tuple",
            "zero-step MoveForward": "stepsmustbe>=0",
        }
        for label, fragment in forbidden_api_fragments.items():
            if fragment in normalized_api:
                issues.append("Full API forbids {} ({})".format(label, fragment))
        normalized_scope = "".join(" ".join(map(str, test_scope_entries)).split()).lower()
        if len(test_scope_entries) != 4:
            issues.append(
                "Test Scope Plan must contain exactly four rows (found {})".format(
                    len(test_scope_entries)
                )
            )
        required_scope_fragments = {
            "runtime fixture": "run_demo",
            "obstacle fixture": "obstacle",
            "projectile fixture": "projectile",
            "scoring assertion": "score",
            "same-tick projectile position": "(3,2)",
            "second-tick hit position": "(4,2)",
            "reset fixture": "reset",
            "reset snapshot assertion": "snapshot",
            "reset score keys": "p1",
        }
        for label, fragment in required_scope_fragments.items():
            if fragment not in normalized_scope:
                issues.append(
                    "Test Scope Plan missing {} ({})".format(label, fragment)
                )
    if unit["unit_id"] in {
        "p08_excel_data_processing_python",
        "p09_qr_code_gen_det_python",
        "p10_crud_system_java",
        "p11_custom_press_releases_java",
    }:
        task_dir = repo_path / "docs" / "task"
        task_docs = sorted(task_dir.glob("*.json")) if task_dir.exists() else []
        full_api_parts: List[str] = []
        logic_parts: List[str] = []
        test_scope_entries: List[Any] = []
        for task_path in task_docs:
            try:
                task_data = load_json(task_path)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
            full_api_parts.append(str(task_data.get("Full API spec", "")))
            logic_parts.append(str(task_data.get("Logic Analysis", "")))
            test_scope = task_data.get("Test Scope Plan", [])
            if isinstance(test_scope, list):
                test_scope_entries.extend(test_scope)
        normalized_api = "".join(" ".join(full_api_parts).split()).lower()
        normalized_logic = "".join(" ".join(logic_parts).split()).lower()
        normalized_scope = "".join(
            " ".join(map(str, test_scope_entries)).split()
        ).lower()
        if unit["unit_id"] == "p08_excel_data_processing_python":
            required_api_fragments = {
                "model ownership": "model.pyisthesoledefinitionsiteforcell,row,andsheet",
                "one-way dependency": "model.pyimportsnoprojectmodule",
                "canonical operation": "aggregate_column(sheet:sheet,column:int)",
                "CSV loader": "loads_csv(text:str)->sheet",
                "CSV fixture": 'loads_csv("name,value\\na,1\\nb,\\n")',
                "three-test limit": "exactlythree",
            }
            required_scope_fragments = {
                "runtime": "run_demo",
                "operations": "aggregate_column",
                "operation fixture": '[[3,"c"],[1,"a"],[2,"b"],[none,""]] ',
                "filter predicate": "row.values()[0]>=2",
                "CSV": "loads_csv",
                "report": "build_report",
            }
        elif unit["unit_id"] == "p09_qr_code_gen_det_python":
            required_api_fragments = {
                "built-in bytes": "python'sbuilt-inbytestype",
                "forbidden typing bytes": "fromtypingimportbytes",
                "fixed matrix": "size=21",
                "fixed finder": "finder_size=5",
                "wire format": "8-bitunsignedbytelength",
                "checksum": "sum(data)%256",
                "zero matrix padding": "trailingmatrix-paddingbittobezero",
                "direct codec pipeline": "unpack_payload(extract_bits(matrix)).decode",
                "three-test limit": "exactlythree",
            }
            required_scope_fragments = {
                "runtime": "run_demo",
                "Unicode round trip": 'generate("hello-\u4e16\u754c")',
                "padding-aware unpack": "unpack_payload(extract_bits(matrix))",
                "finder corruption": "corrupted[0][0]",
                "malformed matrix": "[[0,1],[1,0]]",
                "decode rejection": "valueerror",
            }
        elif unit["unit_id"] == "p10_crud_system_java":
            required_api_fragments = {
                "plain User class": "publicfinalclassuser",
                "plain AuditEvent class": "publicfinalclassauditevent",
                "Java 11 record prohibition": (
                    "javarecordsyntaxisforbiddenunderjava11",
                    "java11only;javarecordsyntaxisforbidden",
                ),
                "User private final fields": (
                    "privatefinalstringid,name,andemail",
                    "fields(privatefinal):stringid,stringname,stringemail",
                ),
                "fixed audit timestamp": (
                    "explicitfixedtimestamps",
                    "fixedtimestamp1640995200000l",
                    "withtimestamp1640995200000l",
                ),
                "non-validating User constructor": (
                    "storesitsthreeargumentsunchanged",
                    "storesargumentsunchanged",
                ),
                "separate validator": (
                    "uservalidatoralonechecksnull/blankfields",
                    "validationseparatedintouservalidator",
                ),
                "name-token search": (
                    "whitespace-delimitedname-tokenmatching",
                    "exactname-tokensearch",
                    "whitespace-delimitedtokens",
                ),
                "explicit audit": (
                    "auditisexplicitandnevercoupled",
                    "auditisexplicitanddecoupled",
                ),
                "UserRepository List import": "importjava.util.list;",
                "Main collection-free demo": (
                    "main.javamustcontainnocollectiontypedeclaration",
                    "main.javacontainsnocollectiontypedeclaration",
                ),
                "three-test limit": "exactlythree",
            }
            required_scope_fragments = {
                "runtime": "main.main",
                "ordinary entities": (
                    "ordinaryuserandauditevent",
                    "runtimeplusvalue-objects",
                ),
                "fixed timestamp": "1640995200000l",
                "validation fixture": 'newuser("",null,"")',
                "search fixture": "alicesmith",
                "search query": '"smith"',
                "CRUD upsert": "upsert",
                "explicit audit": "explicit",
                "create event": "create_user",
                "delete event": "delete_user",
            }
            if "definesuserrecord" in normalized_logic:
                issues.append("Logic Analysis still defines User as a Java record")
            if "definesauditeventrecord" in normalized_logic:
                issues.append("Logic Analysis still defines AuditEvent as a Java record")
        else:
            required_api_fragments = {
                "ReleaseState owner": "releasestate.javaisthesoledefinitionsite",
                "Version owner": "version.javaisthesoledefinitionsite",
                "ReleaseState enum": "publicenumreleasestate{draft,review,published}",
                "Version class": "publicfinalclassversion",
                "Template API": "applycustomfields(map<string,string>fields)",
                "lifecycle": "submitforreview()",
                "publish": "publish()",
                "tag search": "searchbytag(list<pressrelease>releases,stringtag)",
                "three-test limit": "exactlythree",
                "Java 11": "post-java-11syntaxareforbidden",
            }
            required_scope_fragments = {
                "runtime": "main.main",
                "template fixture": '{{headline}}|{{body}}|{{contact}}',
                "rendered fixture": "hello|body|a@b.com",
                "validation": "validator",
                "release id": '"r1"',
                "draft": "draft",
                "review": "review",
                "published": "published",
                "tag": '"media"',
                "version": "versionnumber1",
            }
        if not normalized_api:
            issues.append("missing project-contract Full API specification")
        for label, fragment_or_options in required_api_fragments.items():
            options = (
                fragment_or_options
                if isinstance(fragment_or_options, tuple)
                else (fragment_or_options,)
            )
            if not any(fragment in normalized_api for fragment in options):
                issues.append(
                    "Full API missing {} ({})".format(label, " or ".join(options))
                )
        if len(test_scope_entries) != 3:
            issues.append(
                "Test Scope Plan must contain exactly three rows (found {})".format(
                    len(test_scope_entries)
                )
            )
        for label, fragment_or_options in required_scope_fragments.items():
            options = (
                fragment_or_options
                if isinstance(fragment_or_options, tuple)
                else (fragment_or_options,)
            )
            if not any(fragment.strip() in normalized_scope for fragment in options):
                issues.append(
                    "Test Scope Plan missing {} ({})".format(
                        label, " or ".join(fragment.strip() for fragment in options)
                    )
                )
    if unit["unit_id"] == "p12_video_player_cpp":
        task_dir = repo_path / "docs" / "task"
        task_docs = sorted(task_dir.glob("*.json")) if task_dir.exists() else []
        full_api_parts: List[str] = []
        for task_path in task_docs:
            try:
                task_data = load_json(task_path)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
            full_api_parts.append(str(task_data.get("Full API spec", "")))
        normalized_api = "".join(" ".join(full_api_parts).split()).lower()
        required_api_fragments = {
            "direct cstdint include": "#include<cstdint>",
            "qualified fixed-width type": "std::int64_t",
            "exact IClock signature": (
                "virtualstd::int64_tnow_ms()constnoexcept=0;",
                "virtualstd::int64_tnow_ms()constnoexcept=0",
            ),
            "bare type prohibition": "bare`int64_t`isforbidden",
            "consistent override rule": "consistentoverriderule",
            "self-contained test main": "self-containedzero-third-partytestexecutablewithexactlyone`intmain()`",
            "GoogleTest prohibition": "googletest",
            "direct CMake test executable": "add_executable(video_player_teststests/test_main.cpp)",
            "minimal runtime entry": "returns`runtime::app().run_demo()`",
        }
        if not normalized_api:
            issues.append("missing project-contract Full API specification")
        for label, fragment_or_options in required_api_fragments.items():
            options = (
                fragment_or_options
                if isinstance(fragment_or_options, tuple)
                else (fragment_or_options,)
            )
            if not any(fragment in normalized_api for fragment in options):
                issues.append(
                    "Full API missing {} ({})".format(label, " or ".join(options))
                )
    return issues


def architecture_validation(unit: Dict[str, Any]) -> Dict[str, Any]:
    team_path = team_dir(unit) / "team.json"
    repo_path = initial_project_dir(unit)
    filenames = code_todo_filenames(team_path) if team_path.exists() else []
    missing = sorted(set(required_files(unit["language"])) - set(filenames))
    duplicates = sorted({name for name in filenames if filenames.count(name) > 1})
    target_file_count = int(unit["targets"]["files"])
    minimum_file_count = max(3, target_file_count - 1)
    maximum_file_count = target_file_count + 1
    file_count_in_range = minimum_file_count <= len(filenames) <= maximum_file_count
    contract_issues = unit_architecture_contract_issues(unit, filenames, repo_path)
    valid = bool(
        team_path.exists()
        and repo_path.exists()
        and filenames
        and not missing
        and not duplicates
        and not contract_issues
    )
    return {
        "valid": valid,
        "team_json": str(team_path),
        "team_json_sha256": sha256_file(team_path) if team_path.exists() else None,
        "initial_repository": str(repo_path),
        "initial_repository_tree_sha256": tree_hash(repo_path) if repo_path.exists() else None,
        "planned_files": filenames,
        "planned_file_count": len(filenames),
        "target_file_count": target_file_count,
        "accepted_file_count_range": [minimum_file_count, maximum_file_count],
        "file_count_in_range": file_count_in_range,
        "file_count_reference_only": True,
        "missing_required_files": missing,
        "duplicate_planned_files": duplicates,
        "project_contract_issues": contract_issues,
    }


def architecture_is_valid(unit: Dict[str, Any]) -> bool:
    try:
        return bool(architecture_validation(unit)["valid"])
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def refresh_architecture_evidence(unit: Dict[str, Any]) -> None:
    """Persist a corrected validation result without changing the architecture epoch."""
    validation = architecture_validation(unit)
    if not validation["valid"]:
        return
    evidence_path = architecture_dir(unit) / "evidence.json"
    try:
        evidence = load_json(evidence_path) if evidence_path.exists() else {}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        evidence = {}
    evidence.update(validation)
    evidence["unit_id"] = unit["unit_id"]
    evidence["status"] = "complete"
    evidence["revalidated_at"] = utc_now()
    atomic_json(evidence_path, evidence)


def architecture_matches_current_inputs(
    unit: Dict[str, Any], framework_sha256: str
) -> bool:
    """Whether the latest architecture used the current frozen generation inputs.

    The framework tree alone is insufficient because architecture constraints
    live in this campaign's per-unit prompt as well.  In particular, layout and
    test-contract refinements must invalidate older, otherwise well-formed
    architectures before another seed is spent on them.
    """
    evidence_path = architecture_dir(unit) / "evidence.json"
    if not evidence_path.exists() or not architecture_is_valid(unit):
        return False
    try:
        evidence = load_json(evidence_path)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False
    expected_prompt_sha256 = sha256_bytes(
        build_architecture_prompt(unit).encode("utf-8")
    )
    return (
        evidence.get("framework_tree_sha256") == framework_sha256
        and evidence.get("prompt_sha256") == expected_prompt_sha256
    )


async def architecture_one(
    unit: Dict[str, Any], force: bool, replace_accepted: bool = False
) -> int:
    arch_dir = architecture_dir(unit)
    repo_path = initial_project_dir(unit)
    prompt_path = arch_dir / "prompt.txt"
    evidence_path = arch_dir / "evidence.json"

    # Accepted artifacts must remain paired with the exact architecture and
    # initial-repository hashes recorded by their seed attempt.  Never replace
    # them, even if a stale selection was computed just before acceptance.
    if accepted_is_valid(unit) and not replace_accepted:
        print("[architecture] skip accepted {}".format(unit["unit_id"]))
        return 0

    if replace_accepted and not force:
        raise ValueError("--replace-accepted requires --force")

    if architecture_is_valid(unit) and not force:
        refresh_architecture_evidence(unit)
        print("[architecture] skip valid {}".format(unit["unit_id"]))
        return 0

    # Preserve failed/forced architecture epochs as evidence instead of
    # silently overwriting them.  The initial repository and every seed tried
    # against it belong to that epoch, so archive all three together. Accepted
    # artifacts are never touched because of the guard above.
    if unit_dir(unit).exists() and (force or not architecture_is_valid(unit)):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        failures_root = unit_dir(unit) / "architecture_failures"
        failures_root.mkdir(parents=True, exist_ok=True)
        destination = failures_root / stamp
        suffix = 1
        while destination.exists():
            destination = failures_root / "{}_{}".format(stamp, suffix)
            suffix += 1
        prior_attempts_root = unit_dir(unit) / "attempts"
        initial_root = unit_dir(unit) / "initial_repository"
        accepted_root = accepted_dir(unit)
        prior_replays_root = replays_dir(unit)
        if (
            arch_dir.exists()
            or prior_attempts_root.exists()
            or initial_root.exists()
            or (replace_accepted and accepted_root.exists())
            or (replace_accepted and prior_replays_root.exists())
        ):
            if arch_dir.exists():
                shutil.move(str(arch_dir), str(destination))
            else:
                destination.mkdir(parents=True)
            if prior_attempts_root.exists():
                shutil.move(
                    str(prior_attempts_root), str(destination / "attempts")
                )
            if initial_root.exists():
                shutil.move(
                    str(initial_root), str(destination / "initial_repository")
                )
            if replace_accepted and accepted_root.exists():
                shutil.move(str(accepted_root), str(destination / "accepted"))
            if replace_accepted and prior_replays_root.exists():
                shutil.move(str(prior_replays_root), str(destination / "replays"))

    arch_dir.mkdir(parents=True, exist_ok=True)
    repo_path.parent.mkdir(parents=True, exist_ok=True)
    prompt = build_architecture_prompt(unit)
    prompt_path.write_text(prompt, encoding="utf-8")

    prior_failures = list((unit_dir(unit) / "architecture_failures").glob("*"))
    evidence: Dict[str, Any] = {
        "unit_id": unit["unit_id"],
        "status": "running",
        "started_at": utc_now(),
        "prompt_sha256": sha256_file(prompt_path),
        "architecture_attempt": len(prior_failures) + 1,
        "rebuild_reason": ARCHITECTURE_REBUILD_REASON or None,
        "framework_tree_sha256": tree_hash(FRAMEWORK_DIR / "metagpt"),
        "architecture_repair_llm_output": ARCHITECTURE_REPAIR_LLM_OUTPUT,
    }
    atomic_json(evidence_path, evidence)

    # Import only after METAGPT_PROJECT_ROOT has been set by the parent process.
    from metagpt.config2 import Config, config as metagpt_global_config

    # OpenAI-compatible planners already return valid JSON. MetaGPT's legacy
    # repair pass treats C++ tokens such as // and # inside escaped JSON strings
    # as comments and can corrupt an otherwise parseable response. Pin this
    # architecture-only switch explicitly and record it in epoch evidence.
    # Seeded code generation runs in separate worker processes and is unchanged.
    metagpt_global_config.repair_llm_output = ARCHITECTURE_REPAIR_LLM_OUTPUT
    from metagpt.context import Context
    from metagpt.environment import Environment
    from metagpt.roles.architect import Architect
    from metagpt.roles.engineer import Engineer
    from metagpt.roles.product_manager import ProductManager
    from metagpt.roles.project_manager import ProjectManager
    from metagpt.team import Team

    local_cfg = Config.default()
    # Respect the shard endpoint during architecture refreshes so each rebuild
    # uses the same local model instance as the shard it will later seed.
    local_cfg.llm.base_url = MODEL_BASE_URL + "/v0"
    # Architecture normally uses the separately configured planning model.  A
    # fully explicit OpenAI-compatible override lets the campaign continue on
    # a local, pinned model when that provider is unavailable.  Never persist
    # the API key in evidence; the endpoint and model identity are sufficient
    # to distinguish architecture epochs.
    if ARCHITECTURE_BASE_URL:
        from metagpt.configs.llm_config import LLMType

        remote_cfg = Config.from_llm_config(
            {
                "api_type": LLMType.OPENAI,
                "base_url": ARCHITECTURE_BASE_URL,
                "model": ARCHITECTURE_MODEL or str(MODEL_PATH),
                "api_key": os.environ.get(
                    "CODEWM_ARCHITECTURE_API_KEY", "local-not-secret"
                ),
                # The bundled server returns ordinary JSON rather than SSE.
                "stream": False,
            }
        )
    else:
        remote_cfg = Config.from_home("openai.yaml")
        if remote_cfg is None:
            raise RuntimeError(
                "architecture planning config is missing: provide "
                "~/.metagpt/openai.yaml or CODEWM_ARCHITECTURE_BASE_URL"
            )
    # GPT-5 uses part of the completion budget for reasoning. The default 4096
    # repeatedly truncated the large structured PRD emitted by the patched
    # MetaGPT actions, so pin a budget that accommodates reasoning plus JSON.
    remote_cfg.llm.max_token = ARCHITECTURE_MAX_TOKENS
    # MetaGPT 0.8.2 forces inc=True whenever project_path is non-empty. For a
    # fresh architecture, isolate through workspace.path + project_name instead
    # so the Engineer prepares WriteCode todos instead of an incremental
    # WriteCodePlanAndChange action.
    local_cfg.update_via_cli("", unit["project_name"], False, "", 0)
    remote_cfg.update_via_cli("", unit["project_name"], False, "", 0)
    local_cfg.workspace.path = str(repo_path.parent)
    remote_cfg.workspace.path = str(repo_path.parent)
    for cfg in (local_cfg, remote_cfg):
        try:
            cfg.llm.timeout = max(int(getattr(cfg.llm, "timeout", 0) or 0), 1200)
        except Exception:
            pass

    ctx = Context(config=local_cfg)
    company = Team(
        context=ctx,
        env=Environment(context=ctx, desc=(
            "{} / {} / medium".format(unit["task_name"], unit["language"])
        )),
        roles=[
            ProductManager(config=remote_cfg),
            Architect(config=remote_cfg),
            ProjectManager(config=remote_cfg),
            Engineer(config=local_cfg),
        ],
    )
    company.invest(10.0)
    try:
        if remote_cfg is not None:
            # Planning models can summarize the long normative request in the
            # PRD, after which later roles no longer see the exact API/file/test
            # contract.  Use the same staged propagation for both configured
            # remote planners and explicit local overrides.  These remain
            # model-generated architecture documents; the deterministic prompt
            # binding, prompt hash, raw task hash, and backend identity make the
            # transformation auditable as part of this epoch.
            await company.run(n_round=1, idea=prompt, auto_archive=False)
            for prd_path in sorted((repo_path / "docs" / "prd").glob("*.json")):
                prd = load_json(prd_path)
                prd["Original Requirements"] = prompt
                prd["Normative Architecture Requirements"] = prompt
                atomic_json(prd_path, prd)

            await company.run(n_round=1, auto_archive=False)
            for design_path in sorted(
                (repo_path / "docs" / "system_design").glob("*.json")
            ):
                design = load_json(design_path)
                if unit["unit_id"] == "p09_qr_code_gen_det_python":
                    # The full QR fixture contains many nested quoted code
                    # literals. Repeating it verbatim in ProjectManager's JSON
                    # input made the local planner emit the same unescaped JSON
                    # at a fixed location through all six parser retries. The
                    # PRD still preserves the complete prompt, while this
                    # compact binding supplies the task/file/API invariants;
                    # the complete prompt is restored as authoritative Full API
                    # immediately after the task document parses.
                    design["Normative Architecture Requirements"] = (
                        "Binding QR Python task contract: use exactly, in dependency "
                        "order, requirements.txt; qr_code/payload.py; "
                        "qr_code/matrix.py; qr_code/codec.py; qr_code/render.py; "
                        "qr_code/__init__.py; Main.py; tests/test_main.py. payload "
                        "owns UTF-8 bytes plus length and checksum packing; matrix "
                        "owns fixed 21 by 21 storage and three fixed 5 by 5 finder "
                        "markers; codec composes payload and matrix; render depends "
                        "only on matrix; init exports only real symbols; Main and "
                        "exactly three deterministic tests are last. bytes is a "
                        "Python built-in and is never imported from typing. The 366 "
                        "extracted data bits go directly to unpack_payload, which "
                        "parses the length-determined prefix and accepts only zero "
                        "trailing matrix padding; codec must not regroup them. Preserve "
                        "the detailed APIs from the system design; the complete "
                        "original requirement is injected as authoritative task Full "
                        "API after this JSON stage."
                    )
                else:
                    design["Normative Architecture Requirements"] = prompt
                atomic_json(design_path, design)

            await company.run(n_round=1, auto_archive=False)
            raw_task_documents: Dict[str, Any] = {}
            for task_path in sorted((repo_path / "docs" / "task").glob("*.json")):
                task = load_json(task_path)
                raw_task_documents[task_path.name] = task
                task = canonicalize_generated_task_paths(unit, task)
                # The planning model's compact API summary can contradict the
                # evaluator contract (for example by inventing Command.execute).
                # Preserve that raw document separately for audit, then make
                # the original prompt the single authoritative downstream API.
                task["Full API spec"] = (
                    "AUTHORITATIVE NORMATIVE API; supersedes every earlier model "
                    "summary in this architecture:\n\n{}".format(prompt)
                )
                task["Shared Knowledge"] = (
                    "{}\n\nThe full normative architecture prompt above is binding for "
                    "every generated file and test.".format(
                        task.get("Shared Knowledge", "")
                    )
                )
                if unit["unit_id"] == "p06_tank_battle_game_java":
                    task["Test Scope Plan"] = [
                        [
                            "src/test/java/MainTest.java",
                            "runtime: Main.main(new String[0]) returns normally",
                        ],
                        [
                            "src/test/java/MainTest.java",
                            "blocked movement/reset: exact 6x5 Alice/Bob/Position(2,2) obstacle fixture; fetch fresh copies",
                        ],
                        [
                            "src/test/java/MainTest.java",
                            "hit/kill: exact Position(1,2) -> Position(2,2) -> Position(3,2) same-tick fixture; fresh Bob copy, hits1 kills1 score6",
                        ],
                    ]
                elif unit["unit_id"] == "p06_tank_battle_game_python":
                    task["Test Scope Plan"] = [
                        [
                            "tests/test_main.py",
                            "runtime: result=run_demo(); assert exact plain snapshot keys and p1 direction S",
                        ],
                        [
                            "tests/test_main.py",
                            "obstacle: exact Obstacle(Rect(3,1,1,1)) fixture blocks MoveForward(2)",
                        ],
                        [
                            "tests/test_main.py",
                            "projectile-hit/scoring: exact (3,2) same-tick position, (4,2) hit, score and p1 assertions",
                        ],
                        [
                            "tests/test_main.py",
                            "reset: fresh Game then immediately initial=game.snapshot() before any command/tick; no prior Fire; mutate, reset, snapshot equality, empty queues/projectiles, exact zeroed p1/p2 score maps",
                        ],
                    ]
                elif unit["unit_id"] == "p07_calculator_python":
                    task["Test Scope Plan"] = [
                        [
                            "tests/test_main.py",
                            "runtime/arithmetic: run_demo returns dict; evaluate(\"2 + 3 * 4\") equals 14.0",
                        ],
                        [
                            "tests/test_main.py",
                            "history/token count: one History records exactly (\"(1 + 2) * 3\",9.0); len(tokenize(\"1 + 2.5\")) == 3; no token construction or reflection",
                        ],
                        [
                            "tests/test_main.py",
                            "domain errors: division by zero raises EvaluationError, 1 @ 2 raises TokenizationError, blank input raises ParseError",
                        ],
                    ]
                elif unit["unit_id"] == "p08_excel_data_processing_python":
                    task["Test Scope Plan"] = [
                        [
                            "tests/test_main.py",
                            "runtime: run_demo() returns a dict",
                        ],
                        [
                            "tests/test_main.py",
                            "operations: Sheet.from_values([[3,\"c\"],[1,\"a\"],[2,\"b\"],[None,\"\"]]); filter_rows(sheet, lambda row: isinstance(row.values()[0], (int, float)) and row.values()[0] >= 2) keeps exactly [[3,\"c\"],[2,\"b\"]]; sort plus aggregate_column exact count4 missing1 numeric_count3 sum6 min1 max3",
                        ],
                        [
                            "tests/test_main.py",
                            "CSV/report: loads_csv(\"name,value\\nA,1\\nB,\\n\") round-trips through dumps_csv; build_report yields row_count3 column_count2 missing_cells1",
                        ],
                    ]
                elif unit["unit_id"] == "p09_qr_code_gen_det_java":
                    task["Test Scope Plan"] = [
                        [
                            "src/test/java/MainTest.java",
                            "runtime: Main.main(new String[0]) returns normally",
                        ],
                        [
                            "src/test/java/MainTest.java",
                            "nine-bit padding: exact boolean fixture yields unsigned 128,128; hello-\u4e16\u754c round-trip and rendered row count",
                        ],
                        [
                            "src/test/java/MainTest.java",
                            "finder corruption: flip copied matrix finder cell [0][0] and require IllegalArgumentException",
                        ],
                    ]
                elif unit["unit_id"] == "p09_qr_code_gen_det_python":
                    task["Test Scope Plan"] = [
                        [
                            "tests/test_main.py",
                            "runtime: run_demo() exact CodeWM values, size21, rendered_lines21",
                        ],
                        [
                            "tests/test_main.py",
                            "Unicode round trip: generate(\"hello-\u4e16\u754c\"), validate_matrix/detect true, exact decode, unpack_payload(extract_bits(matrix)) accepts trailing zero matrix padding, render 21 lines",
                        ],
                        [
                            "tests/test_main.py",
                            "corruption: [row[:] for row in matrix], flip corrupted[0][0], validate/detect false, decode raises ValueError; [[0,1],[1,0]] invalid",
                        ],
                    ]
                elif unit["unit_id"] == "p10_crud_system_python":
                    task["Test Scope Plan"] = [
                        [
                            "tests/test_main.py",
                            "basic CRUD: FixedClock(100.0,10.0), Repository, AuditTrail() with no clock, Service; create is timestamped 100.0, update is 110.0, and each entity timestamp equals its audit timestamp because Service calls now exactly once per operation",
                        ],
                        [
                            "tests/test_main.py",
                            "errors: duplicate-name creation raises directly imported DuplicateNameError and missing access raises directly imported NotFoundError",
                        ],
                        [
                            "tests/test_main.py",
                            "pagination/audit: create Alpha, Beta, Gamma; limit2 offset1 returns Beta and Gamma; three audit timestamps are exactly [100.0,110.0,120.0]",
                        ],
                    ]
                elif unit["unit_id"] == "p10_crud_system_java":
                    entity_logic = {
                        "src/main/java/User.java": (
                            "domain entity; defines ordinary public final class User "
                            "with private final fields, non-validating constructor that "
                            "stores arguments unchanged, getters, and value methods; "
                            "UserValidator alone checks null/blank fields; Java record "
                            "syntax is forbidden under Java 11"
                        ),
                        "src/main/java/AuditEvent.java": (
                            "domain entity; defines ordinary public final class "
                            "AuditEvent with private final fields, constructor, getters, "
                            "and value methods; Java record syntax is forbidden under "
                            "Java 11"
                        ),
                    }
                    logic_rows = task.get("Logic Analysis", [])
                    if isinstance(logic_rows, list):
                        task["Logic Analysis"] = [
                            [row[0], entity_logic.get(row[0], row[1])]
                            if isinstance(row, list) and len(row) >= 2
                            else row
                            for row in logic_rows
                        ]
                    task["Test Scope Plan"] = [
                        [
                            "src/test/java/MainTest.java",
                            "test 1 runtime/entities: Main.main(new String[0]) returns normally; ordinary User and AuditEvent getters/equality use explicit timestamp 1640995200000L; no Java record syntax",
                        ],
                        [
                            "src/test/java/MainTest.java",
                            "test 2 validation/search: new User(\"\", null, \"\") is constructible and UserValidator returns false; exact case-insensitive name-token search of Alice Smith and Bob Jones for \"smith\" returns only Alice Smith",
                        ],
                        [
                            "src/test/java/MainTest.java",
                            "test 3 CRUD/explicit audit: deterministic save upsert/read/delete id 1; repository never logs; explicitly log fixed CREATE_USER and DELETE_USER AuditEvent values into the same local AuditLogService and assert exactly those two events",
                        ],
                    ]
                elif unit["unit_id"] == "p11_custom_press_releases_python":
                    task["Test Scope Plan"] = [
                        [
                            "tests/test_main.py",
                            "runtime: import with the separate literal line `from Main import run_demo` (never import run_demo from press_releases); run_demo() returns a dict whose state is PUBLISHED",
                        ],
                        [
                            "tests/test_main.py",
                            "template/lifecycle/version: Template('basic','{{headline}}|{{body}}|{{contact_email}}'), Contact('Alice','a@b.com'), and Hello/Body render exactly Hello|Body|a@b.com; state advances DRAFT to REVIEW to PUBLISHED and one VersionEntry has number 1 plus that rendered text",
                        ],
                        [
                            "tests/test_main.py",
                            "validation/search: construct a candidate with blank headline and Contact('', 'invalid') without a constructor exception; candidate.validate() is False and candidate.submit_for_review() raises DomainError; construct a separate valid release with headline Hello, keep it DRAFT, and immediately assert valid_draft.publish() raises InvalidTransitionError before any submit_for_review call on that object; then media/news tags preserve insertion order without duplicates, search_by_tag finds media, and search_text finds hello",
                        ],
                    ]
                elif unit["unit_id"] == "p11_custom_press_releases_java":
                    task["Test Scope Plan"] = [
                        [
                            "src/test/java/MainTest.java",
                            "test 1 runtime: Main.main(new String[0]) returns normally",
                        ],
                        [
                            "src/test/java/MainTest.java",
                            "test 2 template/validation: Template(\"basic\",\"{{headline}}|{{body}}|{{contact}}\") yields Hello|Body|a@b.com; Validator accepts Hello, Body, a@b.com and rejects blank headline and contact invalid",
                        ],
                        [
                            "src/test/java/MainTest.java",
                            "test 3 lifecycle/tag/version: release \"r1\" moves DRAFT to REVIEW to PUBLISHED, tag \"media\" search returns it, rendering is Hello|Body|a@b.com, and history has Version number 1 with the same text",
                        ],
                    ]
                elif unit["unit_id"] == "p12_video_player_java":
                    task["Test Scope Plan"] = [
                        [
                            "src/test/java/MainTest.java",
                            "test 1 clock/end: playlist has one MediaItem duration 5000; new controller starts index 0; play succeeds; advance clock 5000 and onClockAdvanced; snapshot index0 position5000 duration5000 status STOPPED",
                        ],
                        [
                            "src/test/java/MainTest.java",
                            "test 2 seek/navigation: fresh playlist with durations 3000 and 4000; play at index0; seek5000 clamps3000; next reaches index1 position0; second next stays index1; previous reaches index0; second previous stays index0",
                        ],
                        [
                            "src/test/java/MainTest.java",
                            "test 3 volume: set70, mute makes effective0, set30 while muted makes configured volume30/effective0 and updates lastNonMuted, unmute restores configured/effective30",
                        ],
                    ]
                elif unit["unit_id"] == "p13_video_downloader_cpp":
                    task["Test Scope Plan"] = [
                        [
                            "tests/test_main.cpp",
                            "block 1 URL/format: https://example.com and https://example.com/clip are both valid; https:// and http:///path are invalid empty-host URLs; embedded whitespace and malformed URL are invalid; never reject the host-only URL; parse mp4/webm/audio case-insensitively; extension_for returns .mp4/.webm/.mp3",
                        ],
                        [
                            "tests/test_main.cpp",
                            "block 2 safe naming: InMemoryExistingFiles initialized with clip.mp4 plus empty reserved set makes unique_name(clip,.mp4,...) return exactly clip_2.mp4",
                        ],
                        [
                            "tests/test_main.cpp",
                            "block 3 progress: FakeTransferAdapter(12), queue chunk_size 4, one valid enqueue; initial progress 0/12 QUEUED then three ticks expose bytes 4, 8, 12 and final COMPLETED",
                        ],
                        [
                            "tests/test_main.cpp",
                            "block 4 cancellation: fresh queue enqueues one item, ticks once, records progress, cancel succeeds and sets CANCELED, later tick leaves exactly the recorded progress; cancellation of absent id is false",
                        ],
                    ]
                elif unit["unit_id"] == "p13_video_downloader_python":
                    task["Test Scope Plan"] = [
                        [
                            "tests/test_main.py",
                            "runtime: from Main import run_demo; result is a dict with lowercase state completed and transferred/total exactly 12/12 for https://example.com/clip mapped to (12,4)",
                        ],
                        [
                            "tests/test_main.py",
                            "validation: validate_url accepts https and raises InvalidURLError for ftp and blank; DownloadRequest raises InvalidFormatError for invalid format",
                        ],
                        [
                            "tests/test_main.py",
                            "naming: sanitize_filename('my clip') equals my_clip and unique_name('clip.mp4', {'clip.mp4'}) equals literal clip (1).mp4",
                        ],
                        [
                            "tests/test_main.py",
                            "synchronous cancellation: mapping a:(12,4), b:(8,4); enqueue both, cancel first while pending before any process call, then process_all; first is cancelled at 0/12 and second completed at 8/8 with final_name b.mp4; never require external mid-transfer cancellation",
                        ],
                    ]
                elif unit["unit_id"] == "p14_todo_list_app_java":
                    task["Test Scope Plan"] = [
                        [
                            "src/test/java/MainTest.java",
                            "test 1 runtime/demo: Main.main(new String[0]) returns normally; Main.runDemo() at fixed 2023-10-15 returns exact LinkedHashMap values total2 completed1 pending1 overdue0",
                        ],
                        [
                            "src/test/java/MainTest.java",
                            "test 2 CRUD/validation: blank title throws IllegalArgumentException; create Alpha receives id1, edit it to Beta, set completed true, delete succeeds, and repository findAll is empty",
                        ],
                        [
                            "src/test/java/MainTest.java",
                            "test 3 filter/sort: create incomplete Low due 2023-10-16 tagged work, High due 2023-10-17 tagged work/urgent, and Medium with null due tagged home; listTasks(false,null,work) returns exactly High then Low by higher-priority-first order",
                        ],
                        [
                            "src/test/java/MainTest.java",
                            "test 4 summary: at LocalDate.of(2023,10,15), incomplete HIGH due 2023-10-14 plus incomplete LOW due 2023-10-16 plus completed MEDIUM due 2023-10-14 yields total3 completed1 pending2 overdue1",
                        ],
                    ]
                elif unit["unit_id"] == "p14_todo_list_app_python":
                    task["Test Scope Plan"] = [
                        [
                            "tests/test_main.py",
                            "runtime/basic: from Main import run_demo returns dict; with public todo_app API and FixedClock(date(2023,10,15)), create then complete one task and list it deterministically",
                        ],
                        [
                            "tests/test_main.py",
                            "priority validation: service.create_task(\"Test\", priority=\"invalid\") raises todo_app.ValidationError specifically; ValueError is not accepted",
                        ],
                        [
                            "tests/test_main.py",
                            "stable sorting: create two tasks with identical due_date date(2023,10,16); SortKey.DUE_DATE ascending returns lower id first",
                        ],
                        [
                            "tests/test_main.py",
                            "completion/summary: complete the same task twice and preserve first completed_at date(2023,10,15); summary exact total1 completed1 pending0 completed_today1 and uppercase LOW/MEDIUM/HIGH priority counts",
                        ],
                    ]
                elif unit["unit_id"] == "p14_todo_list_app_cpp":
                    task["Test Scope Plan"] = [
                        [
                            "tests/test_main.cpp",
                            "block 1 basic wiring: create two local tasks, list with global SortOrder::ByDueThenPriority, and verify deterministic order plus summarize completed/pending counts",
                        ],
                        [
                            "tests/test_main.cpp",
                            "block 2 invalid data with fresh local store/manager: first create `const auto existing_id = manager.create_task(\"Existing\", \"\", \"\", Priority::Low, {});`; create_task rejects blank title and invalid nonempty date; edit_task on a missing arbitrary id returns false; edit_task(existing_id, blank title, ...) throws invalid_argument; never reference an id declared in another block",
                        ],
                        [
                            "tests/test_main.cpp",
                            "block 3 normalized tags and ordering with fresh local store/manager: named expected vectors are declared outside assert; require-all tag filtering works; valid due dates sort before empty dates, then higher Priority/title/id; ByTitle sorts title then id; use global unqualified SortOrder",
                        ],
                    ]
                atomic_json(task_path, task)

            if raw_task_documents:
                raw_task_path = arch_dir / "model_task_raw.json"
                atomic_json(raw_task_path, raw_task_documents)
                evidence["model_task_raw_sha256"] = sha256_file(raw_task_path)

            await company.run(n_round=2)
            evidence["architecture_requirement_propagation"] = (
                "full prompt copied into PRD and made the authoritative task Full "
                "API before downstream roles; QR Python uses a compact binding in "
                "system design to keep planner JSON valid, all other units copy the "
                "full prompt there; raw model task preserved by hash"
            )
            evidence["task_path_normalization"] = (
                "bare Java filenames mapped to Maven source roots; already-qualified paths unchanged"
                if unit["language"] == "java"
                else "not required for this language"
            )
        else:
            await company.run(n_round=5, idea=prompt)
        # Team.run deliberately swallows the local /v0 failure and serializes.
        company.serialize(stg_path=team_dir(unit))
        sanitize_team_json(team_dir(unit) / "team.json")
        validation = architecture_validation(unit)
        evidence.update(validation)
        evidence["status"] = "complete" if validation["valid"] else "invalid"
        evidence["completed_at"] = utc_now()
        evidence["architecture_model"] = {
            "api_type": str(getattr(remote_cfg.llm, "api_type", "")),
            "base_url": str(getattr(remote_cfg.llm, "base_url", "")),
            "model": str(getattr(remote_cfg.llm, "model", "")),
        }
        atomic_json(evidence_path, evidence)
        if not validation["valid"]:
            print("[architecture] invalid {}: {}".format(unit["unit_id"], validation))
            return 2
        print(
            "[architecture] complete {} planned_files={}".format(
                unit["unit_id"], validation["planned_file_count"]
            )
        )
        return 0
    except Exception as exc:
        evidence.update(
            {
                "status": "failed",
                "completed_at": utc_now(),
                "error": "{}: {}".format(exc.__class__.__name__, exc),
            }
        )
        atomic_json(evidence_path, evidence)
        raise


def architecture_child(
    unit: Dict[str, Any], force: bool, replace_accepted: bool = False
) -> int:
    return asyncio.run(architecture_one(unit, force, replace_accepted))


def architecture_parent(
    units: Sequence[Dict[str, Any]],
    force: bool,
    rebuild_reason: Optional[str] = None,
    replace_accepted: bool = False,
) -> int:
    if replace_accepted and not force:
        raise ValueError("--replace-accepted requires --force")
    failures = 0
    for index, unit in enumerate(units, start=1):
        if architecture_is_valid(unit) and not force:
            refresh_architecture_evidence(unit)
            print("[architecture] {}/{} skip {}".format(index, len(units), unit["unit_id"]))
            continue
        arch_dir = architecture_dir(unit)
        arch_dir.mkdir(parents=True, exist_ok=True)
        log_path = arch_dir / "architecture.log"
        runtime_root = arch_dir / "metagpt_runtime"
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "_architecture-one",
            "--unit",
            unit["unit_id"],
        ]
        if force:
            command.append("--force")
        if replace_accepted:
            command.append("--replace-accepted")
        child_env = dict(os.environ)
        if rebuild_reason is not None:
            # A long-lived seed supervisor may itself have been launched from
            # a shell containing a reason for an earlier manual rebuild. Never
            # let that ambient label leak into an unrelated automatic epoch.
            child_env["CODEWM_ARCHITECTURE_REBUILD_REASON"] = rebuild_reason
        child_env["METAGPT_PROJECT_ROOT"] = str(runtime_root)
        child_env["PYTHONPATH"] = os.pathsep.join(
            [
                str(FRAMEWORK_DIR),
                str(TOOLS_DIR),
                str(CODEGEN_DIR),
                child_env.get("PYTHONPATH", ""),
            ]
        ).rstrip(os.pathsep)
        print("[architecture] {}/{} start {}".format(index, len(units), unit["unit_id"]))
        result = run_capture(command, cwd=REPO_ROOT, env=child_env, timeout=3600)
        log_path.write_text(result["output"], encoding="utf-8")
        if result["return_code"] != 0:
            failures += 1
            print(
                "[architecture] failed {} rc={} log={}".format(
                    unit["unit_id"], result["return_code"], log_path
                )
            )
        else:
            print("[architecture] complete {}".format(unit["unit_id"]))
        refresh_state()
    return 1 if failures else 0


def raw_attempt_dirs(unit: Dict[str, Any]) -> List[Path]:
    root = unit_dir(unit) / "attempts"
    if not root.exists():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir())


def attempt_dirs(unit: Dict[str, Any]) -> List[Path]:
    """Return attempts belonging to the current architecture epoch only."""
    architecture_evidence_path = architecture_dir(unit) / "evidence.json"
    if not architecture_evidence_path.exists():
        return []
    try:
        architecture_evidence = load_json(architecture_evidence_path)
        current_team_sha256 = architecture_evidence["team_json_sha256"]
        current_initial_sha256 = architecture_evidence[
            "initial_repository_tree_sha256"
        ]
    except (KeyError, OSError, ValueError, TypeError, json.JSONDecodeError):
        return []

    current: List[Path] = []
    for path in raw_attempt_dirs(unit):
        evidence_path = path / "evidence.json"
        if not evidence_path.exists():
            continue
        try:
            evidence = load_json(evidence_path)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
        if (
            evidence.get("architecture_team_sha256") == current_team_sha256
            and evidence.get("initial_repository_tree_sha256")
            == current_initial_sha256
        ):
            current.append(path)
    return current


def next_attempt_number(unit: Dict[str, Any]) -> int:
    numbers: List[int] = []
    for path in attempt_dirs(unit):
        prefix = path.name.split("_", 1)[0]
        if prefix.isdigit():
            numbers.append(int(prefix))
    return max(numbers, default=0) + 1


def random_seed() -> int:
    value = 0
    while value == 0:
        value = secrets.randbits(32)
    return value


def accepted_is_valid(unit: Dict[str, Any]) -> bool:
    root = accepted_dir(unit)
    evidence_path = root / "evidence.json"
    seed_path = root / "seed.json"
    repository = root / "repository"
    architecture_evidence_path = architecture_dir(unit) / "evidence.json"
    if not (
        evidence_path.exists()
        and seed_path.exists()
        and repository.exists()
        and architecture_evidence_path.exists()
    ):
        return False
    try:
        evidence = load_json(evidence_path)
        seed = load_json(seed_path)
        architecture_evidence = load_json(architecture_evidence_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    return bool(
        evidence.get("passed") is True
        and evidence.get("generation_complete") is True
        and evidence.get("evaluator_return_code") == 0
        and int(seed.get("rng_seed", 0)) > 0
        and evidence.get("accepted_repository_tree_sha256") == tree_hash(repository)
        and evidence.get("architecture_team_sha256")
        == architecture_evidence.get("team_json_sha256")
        and evidence.get("initial_repository_tree_sha256")
        == architecture_evidence.get("initial_repository_tree_sha256")
    )


def verified_replay_evidence(unit: Dict[str, Any]) -> List[Path]:
    """Return replay records that regenerated the accepted tree and passed tests."""
    if not accepted_is_valid(unit):
        return []
    accepted_hash = tree_hash(accepted_dir(unit) / "repository")
    verified: List[Path] = []
    for replay in replay_dirs(unit):
        evidence_path = replay / "evidence.json"
        if not evidence_path.exists():
            continue
        try:
            evidence = load_json(evidence_path)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
        if (
            evidence.get("generation_complete") is True
            and evidence.get("evaluator_return_code") == 0
            and evidence.get("passed") is True
            and evidence.get("content_identical_to_accepted") is True
            and evidence.get("accepted_repository_tree_sha256") == accepted_hash
            and evidence.get("replay_repository_tree_sha256") == accepted_hash
        ):
            verified.append(evidence_path)
    return verified


def copy_initial_to_attempt(unit: Dict[str, Any], destination: Path) -> None:
    source = initial_project_dir(unit)
    if not source.exists():
        raise FileNotFoundError("Initial repository not found: {}".format(source))
    shutil.copytree(source, destination)


def normalize_generated_repository(code_root: Path) -> None:
    """Apply the same source cleanup used by ProWES batch_docker."""
    from batch_snapshots import remove_leading_h2_line

    remove_leading_h2_line(code_root)


def copy_canonical_repository(source: Path, destination: Path) -> None:
    """Copy only the repository content that forms the published artifact."""
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(
            ".git",
            "DTResults",
            "__pycache__",
            ".pytest_cache",
            "build",
            "target",
            "*_wm_detRes.txt",
        ),
    )


def evaluate_repository(code_root: Path, log_path: Path) -> Dict[str, Any]:
    normalize_generated_repository(code_root)
    env = dict(os.environ)
    env.update(
        {
            "CTR_NAME": "CodeWM-DT",
            "TIME_LIMIT": "300",
            "INSTALL_TIME_LIMIT": "300",
            "BUILD_TIME_LIMIT": "300",
            "TEST_TIME_LIMIT": "30",
            "RUN_CHECK_SECONDS": "5",
            "RUN_CHECK_KILL_AFTER": "2",
            "RUNTIME_ENABLE_CPU_BUSY_CHECK": "1",
            "RUNTIME_CPU_BUSY_THRESHOLD": "95",
            "RUNTIME_CPU_BUSY_MIN_SAMPLES": "6",
            "ENABLE_MAVEN_PROXY_CONFIG": "1",
            "MAVEN_PROXY_HOST": "192.168.129.183",
            "MAVEN_PROXY_PORT": "7897",
        }
    )
    # The evaluator container is shared.  Serialize evaluations across model
    # shards so Maven/Python package setup and process cleanup cannot race.
    lock_path = REPRO_ROOT / ".evaluator.lock"
    with lock_path.open("a", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        try:
            result = run_capture(
                ["bash", str(TEST_SCRIPT), str(code_root)],
                cwd=REPO_ROOT,
                env=env,
                timeout=480,
            )
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
    log_path.write_text(result["output"], encoding="utf-8")
    result["log_sha256"] = sha256_file(log_path)
    return result


async def seed_attempt(unit: Dict[str, Any], attempt_number: int, seed: int) -> bool:
    from agentCodeGen import codeGen

    attempt_dir = unit_dir(unit) / "attempts" / "{:04d}_seed_{}".format(
        attempt_number, seed
    )
    attempt_project = attempt_dir / unit["project_name"]
    attempt_dir.mkdir(parents=True, exist_ok=False)
    copy_initial_to_attempt(unit, attempt_project)
    evidence_path = attempt_dir / "evidence.json"
    generation_path = attempt_dir / "generation_report.json"
    evaluation_log = attempt_dir / "evaluator.log"
    xargs = dict(manifest()["generation"])
    xargs["rng_seed"] = int(seed)
    current_architecture = load_json(architecture_dir(unit) / "evidence.json")
    architecture_epoch = {
        "architecture_attempt": current_architecture.get("architecture_attempt"),
        "architecture_team_sha256": current_architecture.get("team_json_sha256"),
        "initial_repository_tree_sha256": current_architecture.get(
            "initial_repository_tree_sha256"
        ),
        "prompt_sha256": current_architecture.get("prompt_sha256"),
    }

    evidence: Dict[str, Any] = {
        "unit_id": unit["unit_id"],
        "attempt": attempt_number,
        "rng_seed": seed,
        "started_at": utc_now(),
        "architecture_team_sha256": sha256_file(team_dir(unit) / "team.json"),
        "initial_repository_tree_sha256": tree_hash(initial_project_dir(unit)),
        "architecture_epoch": architecture_epoch,
        "generation_args": xargs,
        "passed": False,
    }
    atomic_json(evidence_path, evidence)

    try:
        report = await codeGen(
            unit["project_name"],
            xargs,
            abort_on_truncation=True,
            project_path=attempt_project,
            recover_root=team_dir(unit),
            model_base_url=MODEL_BASE_URL + "/v1",
        )
        atomic_json(generation_path, report)
        generation_complete = bool(report.get("generation_complete"))
        code_root = attempt_project / attempt_project.name
        if generation_complete and code_root.exists():
            normalize_generated_repository(code_root)
        evidence.update(
            {
                "generation_complete": generation_complete,
                "generation_report_sha256": sha256_file(generation_path),
                "generated_repository": str(code_root),
                "generated_repository_tree_sha256": (
                    tree_hash(code_root) if code_root.exists() else None
                ),
                "truncated_files": list(report.get("truncated_files") or []),
            }
        )
        if not generation_complete:
            evidence["completed_at"] = utc_now()
            evidence["failure_stage"] = "generation"
            atomic_json(evidence_path, evidence)
            return False

        evaluation = evaluate_repository(code_root, evaluation_log)
        passed = evaluation["return_code"] == 0
        evidence.update(
            {
                "evaluator_return_code": evaluation["return_code"],
                "evaluator_elapsed_seconds": evaluation["elapsed_seconds"],
                "evaluator_log_sha256": evaluation["log_sha256"],
                "passed": passed,
                "completed_at": utc_now(),
            }
        )
        atomic_json(evidence_path, evidence)
        if not passed:
            evidence["failure_stage"] = "evaluation"
            atomic_json(evidence_path, evidence)
            return False

        # A forced architecture refresh may run alongside seed workers.  Do
        # not accept a passing repository if its source architecture changed
        # after this attempt copied the initial repository.
        architecture_unchanged = bool(
            (team_dir(unit) / "team.json").exists()
            and initial_project_dir(unit).exists()
            and sha256_file(team_dir(unit) / "team.json")
            == evidence["architecture_team_sha256"]
            and tree_hash(initial_project_dir(unit))
            == evidence["initial_repository_tree_sha256"]
        )
        if not architecture_unchanged:
            evidence.update(
                {
                    "evaluation_passed": True,
                    "passed": False,
                    "failure_stage": "architecture_changed_during_attempt",
                    "completed_at": utc_now(),
                }
            )
            atomic_json(evidence_path, evidence)
            return False

        accepted = accepted_dir(unit)
        if accepted.exists():
            shutil.rmtree(accepted)
        accepted.mkdir(parents=True)
        accepted_repo = accepted / "repository"
        copy_canonical_repository(code_root, accepted_repo)
        accepted_hash = tree_hash(accepted_repo)
        seed_record = {
            "unit_id": unit["unit_id"],
            "rng_seed": seed,
            "attempt": attempt_number,
            "selected_at": utc_now(),
            "generation": xargs,
            "architecture_epoch": architecture_epoch,
        }
        atomic_json(accepted / "seed.json", seed_record)
        accepted_evidence = {
            **evidence,
            "accepted_repository_tree_sha256": accepted_hash,
            "attempt_evidence": str(evidence_path.relative_to(REPRO_ROOT)),
            "attempt_generation_report": str(generation_path.relative_to(REPRO_ROOT)),
            "attempt_evaluator_log": str(evaluation_log.relative_to(REPRO_ROOT)),
            "accepted_at": utc_now(),
        }
        atomic_json(accepted / "evidence.json", accepted_evidence)
        return True
    except Exception as exc:
        evidence.update(
            {
                "completed_at": utc_now(),
                "failure_stage": "exception",
                "error": "{}: {}".format(exc.__class__.__name__, exc),
            }
        )
        atomic_json(evidence_path, evidence)
        raise


def recheck_attempt(unit: Dict[str, Any], attempt_number: int) -> int:
    candidates = [
        path
        for path in attempt_dirs(unit)
        if path.name.startswith("{:04d}_".format(attempt_number))
    ]
    if len(candidates) != 1:
        raise SystemExit(
            "Expected exactly one attempt {} for {}, found {}".format(
                attempt_number, unit["unit_id"], len(candidates)
            )
        )
    attempt_dir = candidates[0]
    evidence_path = attempt_dir / "evidence.json"
    evidence = load_json(evidence_path)
    if not evidence.get("generation_complete"):
        raise SystemExit("Cannot recheck an incomplete generation")
    attempt_project = attempt_dir / unit["project_name"]
    code_root = attempt_project / attempt_project.name
    normalize_generated_repository(code_root)
    existing = sorted(attempt_dir.glob("evaluator_recheck_*.log"))
    log_path = attempt_dir / "evaluator_recheck_{:02d}.log".format(len(existing) + 1)
    previous = {
        "checked_at": evidence.get("completed_at"),
        "return_code": evidence.get("evaluator_return_code"),
        "log_sha256": evidence.get("evaluator_log_sha256"),
        "harness_note": "pre-normalization campaign result" if not existing else "prior recheck",
    }
    history = list(evidence.get("evaluation_history") or [])
    history.append(previous)
    evaluation = evaluate_repository(code_root, log_path)
    passed = evaluation["return_code"] == 0
    evidence.update(
        {
            "generated_repository_tree_sha256": tree_hash(code_root),
            "evaluator_return_code": evaluation["return_code"],
            "evaluator_elapsed_seconds": evaluation["elapsed_seconds"],
            "evaluator_log_sha256": evaluation["log_sha256"],
            "evaluator_log": str(log_path.relative_to(REPRO_ROOT)),
            "evaluation_history": history,
            "passed": passed,
            "completed_at": utc_now(),
            "failure_stage": None if passed else "evaluation",
            "normalization": "batch_snapshots.remove_leading_h2_line",
        }
    )
    atomic_json(evidence_path, evidence)
    if passed:
        accepted = accepted_dir(unit)
        if accepted.exists():
            shutil.rmtree(accepted)
        accepted.mkdir(parents=True)
        accepted_repo = accepted / "repository"
        copy_canonical_repository(code_root, accepted_repo)
        seed_record = {
            "unit_id": unit["unit_id"],
            "rng_seed": int(evidence["rng_seed"]),
            "attempt": int(evidence["attempt"]),
            "selected_at": utc_now(),
            "generation": evidence["generation_args"],
            "architecture_epoch": {
                "architecture_attempt": load_json(
                    architecture_dir(unit) / "evidence.json"
                ).get("architecture_attempt"),
                "architecture_team_sha256": evidence.get(
                    "architecture_team_sha256"
                ),
                "initial_repository_tree_sha256": evidence.get(
                    "initial_repository_tree_sha256"
                ),
                "prompt_sha256": load_json(
                    architecture_dir(unit) / "evidence.json"
                ).get("prompt_sha256"),
            },
        }
        atomic_json(accepted / "seed.json", seed_record)
        accepted_evidence = {
            **evidence,
            "accepted_repository_tree_sha256": tree_hash(accepted_repo),
            "attempt_evidence": str(evidence_path.relative_to(REPRO_ROOT)),
            "attempt_generation_report": str(
                (attempt_dir / "generation_report.json").relative_to(REPRO_ROOT)
            ),
            "attempt_evaluator_log": str(log_path.relative_to(REPRO_ROOT)),
            "accepted_at": utc_now(),
        }
        atomic_json(accepted / "evidence.json", accepted_evidence)
    refresh_state()
    print(
        "[recheck] {} attempt={} rc={} passed={} log={}".format(
            unit["unit_id"], attempt_number, evaluation["return_code"], passed, log_path
        )
    )
    return 0 if passed else 1


async def replay_once(unit: Dict[str, Any]) -> bool:
    """Regenerate an accepted seed without mutating the accepted artifact."""
    from agentCodeGen import codeGen

    if not accepted_is_valid(unit):
        raise RuntimeError("No valid accepted repository for {}".format(unit["unit_id"]))
    seed_record = load_json(accepted_dir(unit) / "seed.json")
    seed = int(seed_record["rng_seed"])
    replay_number = next_replay_number(unit)
    replay_dir = replays_dir(unit) / "{:04d}_seed_{}".format(replay_number, seed)
    replay_project = replay_dir / unit["project_name"]
    replay_dir.mkdir(parents=True, exist_ok=False)
    copy_initial_to_attempt(unit, replay_project)

    evidence_path = replay_dir / "evidence.json"
    generation_path = replay_dir / "generation_report.json"
    evaluation_log = replay_dir / "evaluator.log"
    accepted_repository = accepted_dir(unit) / "repository"
    accepted_hash = tree_hash(accepted_repository)
    xargs = dict(seed_record["generation"])
    xargs["rng_seed"] = seed
    evidence: Dict[str, Any] = {
        "unit_id": unit["unit_id"],
        "replay": replay_number,
        "rng_seed": seed,
        "started_at": utc_now(),
        "architecture_team_sha256": sha256_file(team_dir(unit) / "team.json"),
        "initial_repository_tree_sha256": tree_hash(initial_project_dir(unit)),
        "accepted_repository_tree_sha256": accepted_hash,
        "generation_args": xargs,
        "model_base_url": MODEL_BASE_URL,
        "generation_complete": False,
        "content_identical_to_accepted": False,
        "passed": False,
    }
    atomic_json(evidence_path, evidence)

    try:
        report = await codeGen(
            unit["project_name"],
            xargs,
            abort_on_truncation=True,
            project_path=replay_project,
            recover_root=team_dir(unit),
            model_base_url=MODEL_BASE_URL + "/v1",
        )
        atomic_json(generation_path, report)
        generation_complete = bool(report.get("generation_complete"))
        code_root = replay_project / replay_project.name
        if generation_complete and code_root.exists():
            normalize_generated_repository(code_root)
        evidence.update(
            {
                "generation_complete": generation_complete,
                "generation_report_sha256": sha256_file(generation_path),
                "generated_repository": str(code_root),
                "truncated_files": list(report.get("truncated_files") or []),
            }
        )
        if not generation_complete or not code_root.exists():
            evidence.update({"completed_at": utc_now(), "failure_stage": "generation"})
            atomic_json(evidence_path, evidence)
            return False

        evaluation = evaluate_repository(code_root, evaluation_log)
        canonical_repository = replay_dir / "repository"
        copy_canonical_repository(code_root, canonical_repository)
        replay_hash = tree_hash(canonical_repository)
        identical = replay_hash == accepted_hash
        evaluator_passed = evaluation["return_code"] == 0
        passed = evaluator_passed and identical
        evidence.update(
            {
                "replay_repository_tree_sha256": replay_hash,
                "content_identical_to_accepted": identical,
                "evaluator_return_code": evaluation["return_code"],
                "evaluator_elapsed_seconds": evaluation["elapsed_seconds"],
                "evaluator_log_sha256": evaluation["log_sha256"],
                "passed": passed,
                "failure_stage": (
                    None
                    if passed
                    else "content_mismatch"
                    if evaluator_passed
                    else "evaluation"
                ),
                "completed_at": utc_now(),
            }
        )
        atomic_json(evidence_path, evidence)
        return passed
    except Exception as exc:
        evidence.update(
            {
                "completed_at": utc_now(),
                "failure_stage": "exception",
                "error": "{}: {}".format(exc.__class__.__name__, exc),
            }
        )
        atomic_json(evidence_path, evidence)
        raise


def replay_units(units: Sequence[Dict[str, Any]], force: bool) -> int:
    failures = 0
    for unit in units:
        if verified_replay_evidence(unit) and not force:
            print("[replay] skip verified {}".format(unit["unit_id"]), flush=True)
            continue
        if not accepted_is_valid(unit):
            print("[replay] missing accepted {}".format(unit["unit_id"]), flush=True)
            failures += 1
            continue
        try:
            passed = asyncio.run(replay_once(unit))
        except Exception as exc:
            passed = False
            print(
                "[replay] exception {}: {}: {}".format(
                    unit["unit_id"], exc.__class__.__name__, exc
                ),
                flush=True,
            )
        print("[replay] {} passed={}".format(unit["unit_id"], passed), flush=True)
        if not passed:
            failures += 1
    return 1 if failures else 0


def replay_worker(poll_seconds: int, shard_index: int, shard_count: int) -> int:
    shard_units = [
        unit
        for index, unit in enumerate(all_units())
        if index % shard_count == shard_index
    ]
    print(
        "[replay-worker] shard={}/{} units={} model={}".format(
            shard_index, shard_count, len(shard_units), MODEL_BASE_URL
        ),
        flush=True,
    )
    while True:
        outstanding = [
            unit for unit in shard_units if not verified_replay_evidence(unit)
        ]
        if not outstanding:
            print("[replay-worker] shard complete", flush=True)
            return 0
        ready = [unit for unit in outstanding if accepted_is_valid(unit)]
        if not ready:
            print("[replay-worker] waiting for accepted seeds", flush=True)
            time.sleep(poll_seconds)
            continue
        for unit in ready:
            try:
                passed = asyncio.run(replay_once(unit))
            except Exception as exc:
                print(
                    "[replay-worker] exception {}: {}: {}".format(
                        unit["unit_id"], exc.__class__.__name__, exc
                    ),
                    flush=True,
                )
                return 1
            print(
                "[replay-worker] {} passed={}".format(unit["unit_id"], passed),
                flush=True,
            )
            # Same seed and same frozen endpoint should be deterministic. A
            # mismatch is evidence of an environmental problem, not a reason
            # to loop indefinitely and manufacture a favorable replay.
            if not passed:
                return 3


async def seed_search_one(unit: Dict[str, Any], max_attempts: int) -> int:
    if accepted_is_valid(unit):
        print("[seed] skip accepted {}".format(unit["unit_id"]))
        return 0
    if not architecture_is_valid(unit):
        print("[seed] missing/invalid architecture {}".format(unit["unit_id"]))
        return 2

    start = next_attempt_number(unit)
    for offset in range(max_attempts):
        attempt_number = start + offset
        seed = random_seed()
        print(
            "[seed] {} attempt={} rng_seed={}".format(
                unit["unit_id"], attempt_number, seed
            )
        )
        passed = await seed_attempt(unit, attempt_number, seed)
        refresh_state()
        if passed:
            print("[seed] PASS {} rng_seed={}".format(unit["unit_id"], seed))
            return 0
        print("[seed] fail {} rng_seed={}".format(unit["unit_id"], seed))
    return 3


def seed_search(units: Sequence[Dict[str, Any]], max_attempts: int) -> int:
    failures = 0
    for index, unit in enumerate(units, start=1):
        print("[seed] unit {}/{} {}".format(index, len(units), unit["unit_id"]))
        try:
            rc = asyncio.run(seed_search_one(unit, max_attempts))
        except Exception as exc:
            rc = 1
            print(
                "[seed] exception {}: {}: {}".format(
                    unit["unit_id"], exc.__class__.__name__, exc
                )
            )
        if rc != 0:
            failures += 1
        refresh_state()
    return 1 if failures else 0


def seed_worker(
    max_attempts_per_unit: int,
    poll_seconds: int,
    shard_index: int,
    shard_count: int,
    require_current_framework: bool = False,
    auto_rebuild_stale: bool = False,
) -> int:
    """Consume completed architectures until every unit has an accepted seed.

    A worker locks onto the first ready unit in its shard and keeps drawing new
    random seeds for that unit until one passes. Only then does it advance to
    the next unit. ``max_attempts_per_unit == 0`` means unlimited attempts.
    The current unit lock is persisted per shard, so a restarted supervisor
    resumes the same repository instead of selecting an earlier newly-ready
    architecture.
    """
    shard_units = [
        unit
        for index, unit in enumerate(all_units())
        if index % shard_count == shard_index
    ]
    print(
        "[worker] shard={}/{} units={} model={} require_current_framework={} "
        "auto_rebuild_stale={} max_attempts_per_unit={}".format(
            shard_index,
            shard_count,
            len(shard_units),
            MODEL_BASE_URL,
            require_current_framework,
            auto_rebuild_stale,
            max_attempts_per_unit or "unlimited",
        ),
        flush=True,
    )
    framework_sha256 = tree_hash(FRAMEWORK_DIR / "metagpt")
    locked_unit: Optional[Dict[str, Any]] = None
    lock_path = (
        REPRO_ROOT
        / "worker_state"
        / "seed_shard_{}_of_{}.json".format(shard_index, shard_count)
    )

    if lock_path.exists():
        try:
            saved_lock = load_json(lock_path)
            saved_unit_id = str(saved_lock.get("unit_id", ""))
            matching = [
                unit for unit in shard_units if unit["unit_id"] == saved_unit_id
            ]
            if matching and not accepted_is_valid(matching[0]):
                locked_unit = matching[0]
                print(
                    "[worker] restored_lock={} lock_path={}".format(
                        saved_unit_id, lock_path
                    ),
                    flush=True,
                )
            else:
                lock_path.unlink()
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            print(
                "[worker] ignoring invalid lock {}: {}".format(lock_path, exc),
                flush=True,
            )

    def has_current_architecture(unit: Dict[str, Any]) -> bool:
        if not architecture_is_valid(unit):
            return False
        return not require_current_framework or architecture_matches_current_inputs(
            unit, framework_sha256
        )

    while True:
        state = refresh_state()
        shard_accepted = sum(accepted_is_valid(unit) for unit in shard_units)
        if shard_accepted == len(shard_units):
            if lock_path.exists():
                lock_path.unlink()
            print("[worker] shard complete", flush=True)
            return 0

        if locked_unit is not None and accepted_is_valid(locked_unit):
            print(
                "[worker] completed={} accepted={}/42; advancing".format(
                    locked_unit["unit_id"], state["accepted_count"]
                ),
                flush=True,
            )
            if lock_path.exists():
                lock_path.unlink()
            locked_unit = None
            continue

        if locked_unit is None:
            # Keep acceptance and its exact replay isolated from every later
            # architecture/seed request on this shard's model endpoint, even
            # when the next unit already has a current architecture.
            accepted_without_replay = [
                unit["unit_id"]
                for unit in shard_units
                if accepted_is_valid(unit) and not verified_replay_evidence(unit)
            ]
            if auto_rebuild_stale and accepted_without_replay:
                print(
                    "[worker] waiting for replay before advancing: {}".format(
                        ",".join(accepted_without_replay)
                    ),
                    flush=True,
                )
                time.sleep(poll_seconds)
                continue
            ready_units = [
                unit
                for unit in shard_units
                if not accepted_is_valid(unit) and has_current_architecture(unit)
            ]
            if not ready_units:
                current_or_accepted = sum(
                    accepted_is_valid(unit) or has_current_architecture(unit)
                    for unit in shard_units
                )
                stale_units = [
                    unit
                    for unit in shard_units
                    if not accepted_is_valid(unit)
                    and not has_current_architecture(unit)
                ]
                if auto_rebuild_stale and stale_units:
                    stale_unit = stale_units[0]
                    print(
                        "[worker] rebuilding stale architecture={} before seed search".format(
                            stale_unit["unit_id"]
                        ),
                        flush=True,
                    )
                    try:
                        rebuild_rc = architecture_parent(
                            [stale_unit],
                            force=True,
                            rebuild_reason=(
                                "automatic_stale_input_rebuild_{}".format(
                                    stale_unit["unit_id"]
                                )
                            ),
                        )
                    except Exception as exc:
                        rebuild_rc = 1
                        print(
                            "[worker] architecture exception {}: {}: {}".format(
                                stale_unit["unit_id"], exc.__class__.__name__, exc
                            ),
                            flush=True,
                        )
                    if rebuild_rc != 0:
                        print(
                            "[worker] architecture rebuild failed={}; retrying after {}s".format(
                                stale_unit["unit_id"], poll_seconds
                            ),
                            flush=True,
                        )
                        time.sleep(poll_seconds)
                    continue
                print(
                    "[worker] waiting for shard architecture ({}/{} current or accepted)".format(
                        current_or_accepted, len(shard_units)
                    ),
                    flush=True,
                )
                time.sleep(poll_seconds)
                continue
            # Manifest order makes repository progression deterministic even
            # though every generation seed is randomly drawn.
            locked_unit = ready_units[0]
            atomic_json(
                lock_path,
                {
                    "locked_at": utc_now(),
                    "model_base_url": MODEL_BASE_URL,
                    "shard_count": shard_count,
                    "shard_index": shard_index,
                    "unit_id": locked_unit["unit_id"],
                },
            )
            print(
                "[worker] locked={} accepted={}/42 prior_attempts={}".format(
                    locked_unit["unit_id"],
                    state["accepted_count"],
                    len(attempt_dirs(locked_unit)),
                ),
                flush=True,
            )

        if not has_current_architecture(locked_unit):
            print(
                "[worker] locked={} waiting for its current architecture".format(
                    locked_unit["unit_id"]
                ),
                flush=True,
            )
            time.sleep(poll_seconds)
            continue

        attempts = len(attempt_dirs(locked_unit))
        if max_attempts_per_unit > 0 and attempts >= max_attempts_per_unit:
            print(
                "[worker] stopped: locked unit {} exhausted the per-unit attempt limit".format(
                    locked_unit["unit_id"]
                ),
                flush=True,
            )
            return 3

        print(
            "[worker] retry={} accepted={}/42 prior_attempts={}".format(
                locked_unit["unit_id"], state["accepted_count"], attempts
            ),
            flush=True,
        )
        try:
            asyncio.run(seed_search_one(locked_unit, 1))
        except Exception as exc:
            print(
                "[worker] exception {}: {}: {}".format(
                    locked_unit["unit_id"], exc.__class__.__name__, exc
                ),
                flush=True,
            )
        refresh_state()


def model_weight_manifest(hash_all: bool = False) -> Dict[str, Any]:
    files: List[Dict[str, Any]] = []
    if MODEL_PATH.exists():
        for path in sorted(p for p in MODEL_PATH.iterdir() if p.is_file()):
            entry: Dict[str, Any] = {"name": path.name, "size": path.stat().st_size}
            if hash_all or path.suffix in {".json", ".jinja"} or path.name in {
                "tokenizer_config.json",
                "generation_config.json",
            }:
                entry["sha256"] = sha256_file(path)
            files.append(entry)
    return {
        "path": str(MODEL_PATH),
        "exists": MODEL_PATH.exists(),
        "files": files,
        "all_files_hashed": hash_all,
        "total_bytes": sum(int(entry["size"]) for entry in files),
        "manifest_sha256": sha256_bytes(
            json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ),
    }


def fingerprint_model() -> int:
    evidence_dir = REPRO_ROOT / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    print("[fingerprint] hashing all model files under {}".format(MODEL_PATH), flush=True)
    result = model_weight_manifest(hash_all=True)
    result["captured_at"] = utc_now()
    atomic_json(evidence_dir / "model_weights.json", result)
    print(
        "[fingerprint] files={} bytes={} manifest_sha256={}".format(
            len(result["files"]), result["total_bytes"], result["manifest_sha256"]
        ),
        flush=True,
    )
    return 0 if result["exists"] else 1


def command_version(command: Sequence[str]) -> Dict[str, Any]:
    result = run_capture(command, timeout=30)
    return {
        "command": list(command),
        "return_code": result["return_code"],
        "output": result["output"].strip(),
    }


def preflight() -> int:
    evidence_dir = REPRO_ROOT / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    result: Dict[str, Any] = {
        "captured_at": utc_now(),
        "campaign_manifest_sha256": sha256_file(MANIFEST_PATH),
        "benchmark_git": {
            "head": run_capture(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT)["output"].strip(),
            "status": run_capture(["git", "status", "--short"], cwd=REPO_ROOT)["output"],
        },
        "platform": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": sys.version,
            "python_executable": sys.executable,
        },
        "versions": {
            "podman": command_version(["podman", "--version"]),
            "git": command_version(["git", "--version"]),
            "cmake": command_version(["cmake", "--version"]),
            "java": command_version(["java", "-version"]),
            "gcc": command_version(["gcc", "--version"]),
            "maven": command_version(["mvn", "--version"]),
            "ctags": command_version(["ctags", "--version"]),
        },
        "host": {
            "uname": command_version(["uname", "-a"]),
            "lscpu": command_version(["lscpu"]),
            "locale": command_version(["locale"]),
            "nvidia_smi": command_version(["nvidia-smi"]),
            "gpu_query": command_version(
                [
                    "nvidia-smi",
                    "--query-gpu=index,uuid,name,driver_version,memory.total,compute_cap",
                    "--format=csv,noheader",
                ]
            ),
        },
        "python_packages": {
            "metagpt_environment": command_version(
                [sys.executable, "-m", "pip", "freeze", "--all"]
            ),
            "model_environment": command_version(
                [str(MODEL_PYTHON), "-m", "pip", "freeze", "--all"]
            ),
        },
        "framework": {
            "path": str(FRAMEWORK_DIR / "metagpt"),
            "tree_sha256": tree_hash(FRAMEWORK_DIR / "metagpt"),
        },
        "model_runtime": {
            "path": str(MODEL_RUNTIME_DIR),
            "tree_sha256": tree_hash(MODEL_RUNTIME_DIR),
        },
        "model_weights": model_weight_manifest(),
        "determinism": {
            "strict_pytorch_deterministic_algorithms": "unsupported",
            "observed_error": "Qwen3-MoE CUDA _histc has no deterministic implementation",
            "campaign_mode": "request seed + global RNG lock + fixed runtime fingerprint",
        },
    }
    errors: List[str] = []
    for path in ("/healthz", "/v1/models", "/v1/_processors"):
        try:
            result.setdefault("model_service", {})[path] = http_json(path)
        except Exception as exc:
            errors.append("{}: {}: {}".format(path, exc.__class__.__name__, exc))
    podman = run_capture(
        ["podman", "ps", "--filter", "name=^CodeWM-DT$", "--format", "{{.Names}}\\t{{.Status}}\\t{{.Image}}"],
        timeout=30,
    )
    result["evaluator_container"] = {
        "return_code": podman["return_code"],
        "output": podman["output"].strip(),
        "test_script_sha256": sha256_file(TEST_SCRIPT),
        "protocol_sha256": sha256_file(EVALUATOR_DIR / "docker/eval_protocol.sh"),
        "container_inspect": command_version(["podman", "inspect", "CodeWM-DT"]),
    }
    if podman["return_code"] != 0 or "CodeWM-DT" not in podman["output"]:
        errors.append("CodeWM-DT evaluator container is unavailable")
    if not result["model_weights"]["exists"]:
        errors.append("model weights are unavailable")
    result["errors"] = errors
    result["ready"] = not errors
    atomic_json(evidence_dir / "preflight.json", result)
    print(json.dumps({"ready": result["ready"], "errors": errors}, indent=2))
    return 0 if result["ready"] else 1


def unit_status(unit: Dict[str, Any]) -> Dict[str, Any]:
    arch = architecture_validation(unit) if architecture_is_valid(unit) else {
        "valid": False,
        "planned_file_count": 0,
    }
    accepted = accepted_is_valid(unit)
    seed: Optional[int] = None
    if accepted:
        seed = int(load_json(accepted_dir(unit) / "seed.json")["rng_seed"])
    return {
        "unit_id": unit["unit_id"],
        "project_id": unit["project_id"],
        "task_name": unit["task_name"],
        "language": unit["language"],
        "architecture_valid": bool(arch.get("valid")),
        "planned_file_count": int(arch.get("planned_file_count", 0)),
        "attempt_count": len(attempt_dirs(unit)),
        "accepted": accepted,
        "rng_seed": seed,
        "verified_replay_count": len(verified_replay_evidence(unit)),
    }


def refresh_state() -> Dict[str, Any]:
    statuses = [unit_status(unit) for unit in all_units()]
    state = {
        "updated_at": utc_now(),
        "expected_units": 42,
        "unit_count": len(statuses),
        "architecture_complete_count": sum(s["architecture_valid"] for s in statuses),
        "accepted_count": sum(s["accepted"] for s in statuses),
        "replay_verified_count": sum(s["verified_replay_count"] > 0 for s in statuses),
        "attempt_count": sum(s["attempt_count"] for s in statuses),
        "units": statuses,
    }
    atomic_json(STATE_PATH, state)
    return state


def print_status() -> int:
    state = refresh_state()
    print(
        "units={unit_count}/{expected_units} architecture={architecture_complete_count}/42 "
        "accepted={accepted_count}/42 replayed={replay_verified_count}/42 "
        "attempts={attempt_count}".format(**state)
    )
    for unit in state["units"]:
        print(
            "{unit_id}\tarch={architecture_valid}\tattempts={attempt_count}\t"
            "accepted={accepted}\treplays={verified_replay_count}\tseed={rng_seed}".format(**unit)
        )
    return 0


def repository_metrics(repository: Path, language: str) -> Dict[str, Any]:
    source_extensions = {
        "cpp": {".cpp", ".cc", ".cxx", ".h", ".hpp"},
        "java": {".java"},
        "python": {".py"},
    }[language]
    files = [
        path
        for path in sorted(repository.rglob("*"))
        if path.is_file() and not any(ignored_tree_part(part) for part in path.parts)
    ]
    source_files = [path for path in files if path.suffix.lower() in source_extensions]
    physical_source_loc = 0
    for path in source_files:
        physical_source_loc += len(path.read_text(encoding="utf-8", errors="replace").splitlines())

    language_name = {"cpp": "C++", "java": "Java", "python": "Python"}[language]
    kinds_option = {
        "cpp": "--kinds-C++=f",
        "java": "--kinds-Java=m",
        "python": "--kinds-Python=fm",
    }[language]
    function_count: Optional[int] = None
    if source_files and shutil.which("ctags"):
        tags = run_capture(
            [
                "ctags",
                "--output-format=json",
                "-f",
                "-",
                "--languages={}".format(language_name),
                kinds_option,
                *[str(path) for path in source_files],
            ],
            timeout=60,
        )
        if tags["return_code"] == 0:
            function_count = sum(
                1
                for line in tags["output"].splitlines()
                if line.lstrip().startswith("{") and '\"_type\": \"tag\"' in line
            )
    return {
        "repository_file_count": len(files),
        "source_file_count": len(source_files),
        "physical_source_loc": physical_source_loc,
        "ctags_function_or_method_count": function_count,
        "metric_definition": (
            "files=canonical artifact files; loc=physical lines in language source/header "
            "files; functions=Universal Ctags function/method symbols"
        ),
    }


def write_results(units: Sequence[Dict[str, Any]]) -> None:
    rows: List[Dict[str, Any]] = []
    for unit in units:
        architecture = architecture_validation(unit) if architecture_is_valid(unit) else {}
        architecture_evidence = (
            load_json(architecture_dir(unit) / "evidence.json")
            if architecture_is_valid(unit)
            else {}
        )
        accepted = accepted_is_valid(unit)
        seed_record = load_json(accepted_dir(unit) / "seed.json") if accepted else {}
        accepted_evidence = (
            load_json(accepted_dir(unit) / "evidence.json") if accepted else {}
        )
        repository = accepted_dir(unit) / "repository"
        metrics = repository_metrics(repository, unit["language"]) if accepted else {}
        verified = verified_replay_evidence(unit)
        rows.append(
            {
                "unit_id": unit["unit_id"],
                "project_id": int(unit["project_id"]),
                "category": unit["category"],
                "task_name": unit["task_name"],
                "language": unit["language"],
                "size_tier": manifest()["size_tier"],
                "target_files": int(unit["targets"]["files"]),
                "target_functions": int(unit["targets"]["functions"]),
                "target_loc": int(unit["targets"]["loc"]),
                "planned_files": architecture.get("planned_file_count"),
                "architecture_attempt": architecture_evidence.get(
                    "architecture_attempt"
                ),
                "architecture_api_base_url": architecture_evidence.get(
                    "architecture_model", {}
                ).get("base_url"),
                "architecture_model": architecture_evidence.get(
                    "architecture_model", {}
                ).get("model"),
                "architecture_rebuild_reason": architecture_evidence.get(
                    "rebuild_reason"
                ),
                "architecture_team_sha256": architecture_evidence.get(
                    "team_json_sha256"
                ),
                "initial_repository_tree_sha256": architecture_evidence.get(
                    "initial_repository_tree_sha256"
                ),
                "actual_files": metrics.get("repository_file_count"),
                "actual_source_files": metrics.get("source_file_count"),
                "actual_functions": metrics.get("ctags_function_or_method_count"),
                "actual_physical_source_loc": metrics.get("physical_source_loc"),
                "rng_seed": seed_record.get("rng_seed"),
                "selected_attempt": seed_record.get("attempt"),
                "attempt_count": len(attempt_dirs(unit)),
                "evaluator_return_code": accepted_evidence.get("evaluator_return_code"),
                "accepted_repository_tree_sha256": accepted_evidence.get(
                    "accepted_repository_tree_sha256"
                ),
                "verified_replay_count": len(verified),
                "accepted_evidence": (
                    str((accepted_dir(unit) / "evidence.json").relative_to(REPRO_ROOT))
                    if accepted
                    else None
                ),
            }
        )
    payload = {
        "generated_at": utc_now(),
        "campaign_id": manifest()["campaign_id"],
        "metric_definition": (
            "actual_files counts canonical artifact files; actual_physical_source_loc "
            "counts physical lines in source/header files; actual_functions counts "
            "Universal Ctags function/method symbols"
        ),
        "rows": rows,
    }
    atomic_json(RESULTS_JSON_PATH, payload)
    fieldnames = list(rows[0].keys()) if rows else []
    RESULTS_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = RESULTS_CSV_PATH.with_name("{}.{}.tmp".format(RESULTS_CSV_PATH.name, os.getpid()))
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(RESULTS_CSV_PATH)


def audit() -> int:
    state = refresh_state()
    issues: List[str] = []
    units = all_units()
    if len(units) != 42:
        issues.append("manifest expands to {} units, expected 42".format(len(units)))
    unit_ids = [unit["unit_id"] for unit in units]
    if len(set(unit_ids)) != len(unit_ids):
        issues.append("unit IDs are not unique")

    accepted_seeds: Dict[str, int] = {}
    accepted_hashes: Dict[str, str] = {}
    architecture_model_provenance: Dict[str, Dict[str, Any]] = {}
    replay_evidence: Dict[str, List[str]] = {}
    required_replays = int(manifest()["acceptance"].get("required_replay_confirmations", 0))
    architecture_requirement = manifest().get("architecture_generation", {})
    required_architecture_base_url = str(
        architecture_requirement.get("base_url", "")
    ).rstrip("/")
    required_architecture_model = str(
        architecture_requirement.get("model", "")
    )
    for unit in units:
        if not architecture_is_valid(unit):
            issues.append("{}: missing or invalid architecture".format(unit["unit_id"]))
        else:
            architecture_evidence = load_json(
                architecture_dir(unit) / "evidence.json"
            )
            model_evidence = architecture_evidence.get("architecture_model", {})
            architecture_model_provenance[unit["unit_id"]] = {
                "api_type": model_evidence.get("api_type"),
                "base_url": model_evidence.get("base_url"),
                "model": model_evidence.get("model"),
                "architecture_attempt": architecture_evidence.get(
                    "architecture_attempt"
                ),
                "rebuild_reason": architecture_evidence.get("rebuild_reason"),
            }
            actual_base_url = str(model_evidence.get("base_url", "")).rstrip("/")
            actual_model = str(model_evidence.get("model", ""))
            if (
                actual_base_url != required_architecture_base_url
                or actual_model != required_architecture_model
            ):
                issues.append(
                    "{}: architecture backend {}/{} does not match required {}/{}".format(
                        unit["unit_id"],
                        actual_base_url or "missing",
                        actual_model or "missing",
                        required_architecture_base_url or "missing",
                        required_architecture_model or "missing",
                    )
                )
        if not accepted_is_valid(unit):
            issues.append("{}: missing or invalid accepted result".format(unit["unit_id"]))
            continue
        seed = load_json(accepted_dir(unit) / "seed.json")
        evidence = load_json(accepted_dir(unit) / "evidence.json")
        accepted_seeds[unit["unit_id"]] = int(seed["rng_seed"])
        accepted_hashes[unit["unit_id"]] = str(
            evidence["accepted_repository_tree_sha256"]
        )
        verified = verified_replay_evidence(unit)
        replay_evidence[unit["unit_id"]] = [
            str(path.relative_to(REPRO_ROOT)) for path in verified
        ]
        if len(verified) < required_replays:
            issues.append(
                "{}: has {} verified replay(s), requires {}".format(
                    unit["unit_id"], len(verified), required_replays
                )
            )

    result = {
        "audited_at": utc_now(),
        "campaign_id": manifest()["campaign_id"],
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "campaign_runner_sha256": sha256_file(Path(__file__).resolve()),
        "frozen_framework_tree_sha256": tree_hash(FRAMEWORK_DIR / "metagpt"),
        "frozen_model_runtime_tree_sha256": tree_hash(MODEL_RUNTIME_DIR),
        "frozen_evaluator": {
            "test_script_sha256": sha256_file(TEST_SCRIPT),
            "protocol_sha256": sha256_file(EVALUATOR_DIR / "docker/eval_protocol.sh"),
        },
        "preflight_sha256": (
            sha256_file(REPRO_ROOT / "evidence" / "preflight.json")
            if (REPRO_ROOT / "evidence" / "preflight.json").exists()
            else None
        ),
        "model_weight_manifest_sha256": (
            load_json(REPRO_ROOT / "evidence" / "model_weights.json").get(
                "manifest_sha256"
            )
            if (REPRO_ROOT / "evidence" / "model_weights.json").exists()
            else None
        ),
        "expected_units": 42,
        "architecture_complete_count": state["architecture_complete_count"],
        "accepted_count": state["accepted_count"],
        "accepted_seeds": accepted_seeds,
        "accepted_repository_hashes": accepted_hashes,
        "required_architecture_generation": architecture_requirement,
        "architecture_model_provenance": architecture_model_provenance,
        "required_replay_confirmations": required_replays,
        "verified_replay_count": state["replay_verified_count"],
        "verified_replay_evidence": replay_evidence,
        "issues": issues,
        "complete": not issues and state["accepted_count"] == 42,
    }
    atomic_json(AUDIT_PATH, result)
    write_results(units)
    print(json.dumps({
        "complete": result["complete"],
        "architecture_complete_count": result["architecture_complete_count"],
        "accepted_count": result["accepted_count"],
        "verified_replay_count": result["verified_replay_count"],
        "issue_count": len(issues),
    }, indent=2))
    return 0 if result["complete"] else 1


def selected_units(args: argparse.Namespace) -> List[Dict[str, Any]]:
    stable_unit_indexes = {
        unit["unit_id"]: index for index, unit in enumerate(all_units())
    }
    if getattr(args, "all", False):
        units = all_units()
    elif getattr(args, "unit", None):
        units = [unit_by_id(args.unit)]
    else:
        raise SystemExit("Pass --unit UNIT_ID or --all")

    if getattr(args, "skip_accepted", False):
        units = [unit for unit in units if not accepted_is_valid(unit)]
    if getattr(args, "stale_inputs", False):
        framework_sha256 = tree_hash(FRAMEWORK_DIR / "metagpt")
        units = [
            unit
            for unit in units
            if not architecture_matches_current_inputs(unit, framework_sha256)
        ]
    language = getattr(args, "language", None)
    if language:
        units = [unit for unit in units if unit["language"] == language]
    minimum_attempts = int(getattr(args, "min_failed_attempts", 0) or 0)
    if minimum_attempts:
        units = [unit for unit in units if len(attempt_dirs(unit)) >= minimum_attempts]
    shard_count = int(getattr(args, "shard_count", 1) or 1)
    shard_index = int(getattr(args, "shard_index", 0) or 0)
    if shard_count < 1 or not 0 <= shard_index < shard_count:
        raise SystemExit("Architecture shard index/count are invalid")
    if shard_count > 1:
        units = [
            unit
            for unit in units
            if stable_unit_indexes[unit["unit_id"]] % shard_count == shard_index
        ]
    return units


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)

    sub.add_parser("status")
    sub.add_parser("preflight")
    sub.add_parser("fingerprint-model")
    sub.add_parser("audit")

    for name in ("architecture", "_architecture-one"):
        cmd = sub.add_parser(name)
        group = cmd.add_mutually_exclusive_group(required=True)
        group.add_argument("--unit")
        group.add_argument("--all", action="store_true")
        cmd.add_argument("--force", action="store_true")
        cmd.add_argument(
            "--replace-accepted",
            action="store_true",
            help=(
                "with --force, archive the accepted repository and its replays "
                "with the old architecture epoch before rebuilding"
            ),
        )
        if name == "architecture":
            cmd.add_argument("--skip-accepted", action="store_true")
            cmd.add_argument(
                "--stale-inputs",
                action="store_true",
                help="select architectures whose framework or prompt hash is stale",
            )
            cmd.add_argument("--language", choices=sorted(LANGUAGE_FACTS))
            cmd.add_argument("--min-failed-attempts", type=int, default=0)
            cmd.add_argument("--shard-count", type=int, default=1)
            cmd.add_argument("--shard-index", type=int, default=0)

    seed = sub.add_parser("seed-search")
    group = seed.add_mutually_exclusive_group(required=True)
    group.add_argument("--unit")
    group.add_argument("--all", action="store_true")
    seed.add_argument("--max-attempts", type=int, default=50)
    worker = sub.add_parser("seed-worker")
    worker.add_argument(
        "--max-attempts-per-unit",
        type=int,
        default=0,
        help="stop at this many attempts for the locked unit; 0 is unlimited",
    )
    worker.add_argument("--poll-seconds", type=int, default=20)
    worker.add_argument("--shard-count", type=int, default=1)
    worker.add_argument("--shard-index", type=int, default=0)
    worker.add_argument("--require-current-framework", action="store_true")
    worker.add_argument(
        "--auto-rebuild-stale",
        action="store_true",
        help=(
            "after accepted seeds have verified replays, rebuild the next stale "
            "architecture in this shard before continuing seed search"
        ),
    )
    recheck = sub.add_parser("recheck-attempt")
    recheck.add_argument("--unit", required=True)
    recheck.add_argument("--attempt", type=int, required=True)
    replay = sub.add_parser("replay")
    group = replay.add_mutually_exclusive_group(required=True)
    group.add_argument("--unit")
    group.add_argument("--all", action="store_true")
    replay.add_argument("--force", action="store_true")
    replay_worker_parser = sub.add_parser("replay-worker")
    replay_worker_parser.add_argument("--poll-seconds", type=int, default=20)
    replay_worker_parser.add_argument("--shard-count", type=int, default=1)
    replay_worker_parser.add_argument("--shard-index", type=int, default=0)
    return root


def main() -> int:
    args = parser().parse_args()
    if args.command == "status":
        return print_status()
    if args.command == "preflight":
        return preflight()
    if args.command == "fingerprint-model":
        return fingerprint_model()
    if args.command == "audit":
        return audit()
    if args.command == "architecture":
        return architecture_parent(
            selected_units(args),
            args.force,
            replace_accepted=args.replace_accepted,
        )
    if args.command == "_architecture-one":
        units = selected_units(args)
        if len(units) != 1:
            raise SystemExit("_architecture-one requires exactly one --unit")
        return architecture_child(units[0], args.force, args.replace_accepted)
    if args.command == "seed-search":
        if args.max_attempts < 1:
            raise SystemExit("--max-attempts must be positive")
        return seed_search(selected_units(args), args.max_attempts)
    if args.command == "seed-worker":
        if args.max_attempts_per_unit < 0:
            raise SystemExit("--max-attempts-per-unit must be non-negative")
        if not 1 <= args.poll_seconds <= 60:
            raise SystemExit("--poll-seconds must be in [1, 60]")
        if args.shard_count < 1:
            raise SystemExit("--shard-count must be positive")
        if not 0 <= args.shard_index < args.shard_count:
            raise SystemExit("--shard-index must be in [0, shard-count)")
        return seed_worker(
            args.max_attempts_per_unit,
            args.poll_seconds,
            args.shard_index,
            args.shard_count,
            args.require_current_framework,
            args.auto_rebuild_stale,
        )
    if args.command == "recheck-attempt":
        if args.attempt < 1:
            raise SystemExit("--attempt must be positive")
        return recheck_attempt(unit_by_id(args.unit), args.attempt)
    if args.command == "replay":
        return replay_units(selected_units(args), args.force)
    if args.command == "replay-worker":
        if not 1 <= args.poll_seconds <= 60:
            raise SystemExit("--poll-seconds must be in [1, 60]")
        if args.shard_count < 1:
            raise SystemExit("--shard-count must be positive")
        if not 0 <= args.shard_index < args.shard_count:
            raise SystemExit("--shard-index must be in [0, shard-count)")
        return replay_worker(args.poll_seconds, args.shard_index, args.shard_count)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
