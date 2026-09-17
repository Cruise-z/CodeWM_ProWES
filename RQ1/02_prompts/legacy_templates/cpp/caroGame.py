from typing import Final

desc: Final[str] = "Build C++ project (Caro game, CMake, C++17)."

idea: Final[str] = """
Generate a complete C++17 CMake Caro Game project.

All required files must be generated exactly as specified.

Do not rename, omit, or replace required files.
If your preferred project structure conflicts with the protocol, follow the protocol.

The project must be buildable and runnable in an automated evaluation environment.

The game should implement runtime-relevant Caro Game core logic, such as:

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
* detection of five or more consecutive marks when allowed by the defined rules
* prevention of false wins when marks are interrupted or belong to different players
* game-state tracking, including running, won, and draw states
* winner tracking
* move-result reporting for accepted and rejected moves
* draw detection when the board is full without a winner
* prevention of additional moves after the game has ended
* reset or restart logic when appropriate

The implementation should define clear and deterministic Caro rules.
Unless explicitly configured otherwise, a player should win by placing at least
five consecutive marks horizontally, vertically, or diagonally.

The implementation should use a reasonably modular structure.
Core responsibilities should be separated into reusable modules or classes, such as:

* runtime entry and minimal demonstration
* game lifecycle and turn management
* board representation and board-state operations
* position or coordinate representation
* player and mark representation
* move validation and move-result reporting
* horizontal, vertical, and diagonal win detection
* game-status and winner tracking
* optional presentation or board-rendering logic

The implementation should avoid placing all board management, move validation,
turn switching, win detection, state tracking, rendering, and reset logic in one
large class. Each module or class should have a clear responsibility and contain
meaningful runtime behavior rather than acting as an empty placeholder.

The project should preferably contain around 8 to 10 meaningful C++ source or
header files, including the runtime entry and test file, when this does not
conflict with the required protocol.

The implementation should separate core game logic from presentation/input handling where possible,
so that the core logic can be tested without requiring graphics, keyboard input,
terminal control, random behavior, or real-time interaction.

src/Main.cpp should only provide a minimal runnable demonstration.
The core game logic should be implemented in reusable C++ classes so that tests
can directly validate the runtime behavior.

The core game logic should provide reusable public interfaces that allow tests to:

* create a game with a specified board size
* configure the required winning length
* inspect the current board state
* inspect the mark stored at a specific position
* inspect the current player
* place a mark at a specified row and column
* determine whether a move is valid
* inspect the result of an attempted move
* determine whether the game is running, won, or drawn
* inspect the winning player
* reset the game to its initial state

A valid move should place the current player's mark, check for victory or draw,
and switch players only when the game remains active.

An invalid move should leave the board, current player, winner, and game status
unchanged and should return a clear deterministic rejection result.

The tests must:

* be fully automated
* require no manual interaction
* validate runtime-relevant core logic
* avoid GUI-dependent interaction whenever possible
* return exit code 0 on success and non-zero on failure
* NOT DEPEND ON GoogleTest, Catch2, doctest, or any external testing framework.
* tests/test_main.cpp must be implemented using only the C++17 standard library.

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

The project should avoid external dependencies unless they are explicitly declared in CMakeLists.txt.
The project must compile and pass all tests using CMake and the provided tests/test_main.cpp.
"""