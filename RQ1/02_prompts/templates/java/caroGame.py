from typing import Final

# Short description; edit as needed.

desc: Final[str] = "Build Java project (Caro game, Maven, Java 11)."

idea: Final[str] = """
Generate a complete Java 11 Maven Caro Game project.

All required protocol files must be generated exactly as specified.
Do not rename, omit, relocate, or replace required protocol files.
If your preferred project structure conflicts with the protocol, preserve the
protocol-required files and organize the remaining implementation around them.

The project must be buildable and runnable in an automated evaluation environment.

The game should implement a small but complete Caro game system, including:

* a configurable two-dimensional game board
* two players using distinct marks, such as X and O
* alternating player turns
* placement of marks on valid empty cells
* rejection of moves outside the board
* rejection of moves on occupied cells
* horizontal winning-line detection
* vertical winning-line detection
* main-diagonal winning-line detection
* anti-diagonal winning-line detection
* configurable winning length, using five consecutive marks by default
* game-state tracking
* winner tracking
* move-result reporting
* draw detection when the board is full
* prevention of additional moves after the game has ended
* restart or reset logic when appropriate

The implementation should define clear and deterministic Caro rules.
Unless explicitly configured otherwise, a player should win by placing at least
five consecutive marks horizontally, vertically, or diagonally.

Project structure and module requirements
-----------------------------------------

The generated project must contain between 8 and 10 meaningful production Java
source files.

This count includes the runtime entry file but excludes:

* pom.xml
* automated test files
* documentation
* generated resources

Producing fewer than 8 production Java source files does not satisfy this
requirement.

The implementation must contain the following distinct modules:

* runtime bootstrap
* game orchestration
* board management
* board-position representation
* player representation
* game-state and mark representation
* move validation and move-result handling
* winning-line detection
* optional board presentation or rendering

Each of the following major responsibilities must be implemented in a separate
production Java source file:

* game orchestration
* board management
* player representation
* move validation
* winning-line detection
* runtime bootstrap

Board-position representation, game-state representation, mark representation,
and move-result representation should also be implemented as dedicated domain
types. Lightweight domain types may share a source file only when necessary to
keep the total production source-file count within the required range of 8 to 10.

Do not merge game orchestration, board management, move validation, and
winning-line detection into a single class.

Do not use one generic Rules, Utils, Manager, or Helper class to hold several
unrelated responsibilities.

Do not create empty, placeholder, or artificial classes merely to satisfy the
file-count requirement. Every production source file must contain meaningful
domain state, reusable behavior, or runtime functionality.

Module responsibilities
-----------------------

The runtime-bootstrap module should remain minimal and should only create the
game, perform a small deterministic demonstration, or start an optional
presentation layer. It must not contain core game rules.

The game-orchestration module should manage:

* players
* current turn
* move execution
* game lifecycle
* winner tracking
* draw detection
* game-status transitions
* reset behavior

The board-management module should manage:

* board dimensions
* cell storage
* cell queries
* controlled mark placement
* boundary checks
* occupied-cell checks
* full-board detection
* board clearing

The board-position module should provide a reusable row-and-column coordinate
representation with value-based equality.

The player module should represent player identity and assigned marks.
Players must not directly modify the board without passing through the game
orchestration and validation logic.

The game-state and mark module should explicitly represent:

* empty cells
* the first player's mark
* the second player's mark
* running state
* first-player victory
* second-player victory
* draw state

The move-processing module should validate attempted moves and return a clear
result indicating whether the move was accepted or rejected and why.

The win-detection module should independently implement:

* horizontal sequence detection
* vertical sequence detection
* main-diagonal sequence detection
* anti-diagonal sequence detection
* configurable winning-length support
* detection of uninterrupted lines longer than the required length
* prevention of false wins caused by gaps or mixed marks

An optional presentation module may display the board and game state, but it
must not own the authoritative game state or implement core game rules.

Core logic and public interfaces
--------------------------------

The implementation should separate GUI-independent core logic from any optional
UI code. Core gameplay rules must be testable without launching a GUI window.

The game may include a simple Swing-based or console-based interface, but the
interface must not be required for automated testing.

The core game logic should provide reusable public interfaces that allow tests to:

* create a game with a specified board size
* configure the required winning length
* inspect the current board state
* inspect the mark stored at a specified position
* inspect the current player
* place a mark at a specified row and column
* validate a proposed move
* inspect the result of an attempted move
* determine whether the game is running, won, or drawn
* inspect the winning player
* reset the game to its initial state

A valid move should:

* place the current player's mark
* check horizontal, vertical, and diagonal winning conditions
* check for a draw
* update the game state
* switch players only when the game remains active

An invalid move should:

* leave the board unchanged
* leave the current player unchanged
* leave the winner unchanged
* leave the game status unchanged
* return a clear deterministic rejection result

The tests must:

* be fully automated
* require no manual interaction
* validate runtime-relevant core logic
* avoid GUI-dependent interaction
* contain multiple independent test methods even when only one test file is required
* return exit code 0 on success and non-zero on failure

The automated tests should cover important game logic such as:

* initial board state
* initial player selection
* valid mark placement
* alternating player turns
* rejection of out-of-bounds moves
* rejection of moves on occupied cells
* preservation of the current player after an invalid move
* horizontal win detection
* vertical win detection
* main-diagonal win detection
* anti-diagonal win detection
* detection of five or more consecutive marks
* prevention of false wins when marks are interrupted or belong to different players
* winner and game-over state updates
* prevention of additional moves after a win
* draw detection when the board is full without a winner
* reset or restart behavior when applicable

Before generating code, verify that the planned architecture contains between
8 and 10 production Java source files and that the required major modules are
represented by separate source files.

The project should avoid external dependencies unless they are declared in pom.xml.
The project must compile and pass all tests using mvn test.
"""
