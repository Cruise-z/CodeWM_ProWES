from typing import Final

desc: Final[str] = "Build C++ project (Flappy Bird game, CMake, C++17)."

idea: Final[str] = """
Generate a complete C++17 CMake Flappy Bird Game project.

All required files must be generated exactly as specified.
Do not rename, omit, or replace required files.
If your preferred project structure conflicts with the protocol, follow the protocol.

The project must be buildable and runnable in an automated evaluation environment.

The game should implement runtime-relevant Flappy Bird Game core logic, such as:

* bird state management
* bird vertical movement
* gravity simulation
* flap or jump behavior
* pipe generation
* pipe movement
* upper and lower pipe gap handling
* score tracking when the bird successfully passes pipes
* map boundaries
* collision detection with top and bottom boundaries
* collision detection with upper and lower pipes
* game-over state
* reset or restart logic when appropriate

The implementation should use deterministic update steps so that tests can reliably validate game behavior.
Bird movement, gravity, flap behavior, pipe movement, collision checks, score updates, and game-over transitions should be predictable and testable without relying on real-time input, random behavior, keyboard interaction, or graphical rendering.

The tests must:

* be fully automated
* require no manual interaction
* validate runtime-relevant core logic
* avoid GUI-dependent interaction whenever possible
* return exit code 0 on success and non-zero on failure
* NOT DEPEND ON GoogleTest, Catch2, doctest, or any external testing framework.
* tests/test_main.cpp must be implemented using only the C++17 standard library.

The automated tests should cover important game logic such as:

* initial bird position and game state
* gravity affecting bird velocity or position
* flap behavior changing bird velocity or position
* deterministic game update steps
* pipe creation or configuration
* pipe movement across the map
* pipe gap validation
* collision detection with upper pipes
* collision detection with lower pipes
* collision detection with top and bottom boundaries
* score updates after the bird passes pipes
* game-over detection after collision
* prevention of normal updates after game over when appropriate
* reset or restart behavior when applicable

The implementation should separate core game logic from presentation/input handling where possible,
so that the core logic can be tested without requiring graphics, keyboard input, terminal control, real-time interaction, or random behavior.

The project should provide reusable public interfaces that allow tests to:

* create a game with a specified map width and height
* inspect the bird position and velocity
* trigger a flap action
* advance the game by one update step
* inspect pipe positions and pipe gaps
* add or configure pipes for deterministic testing
* determine whether the bird collides with a pipe or boundary
* inspect the current score
* determine whether the game is running or over
* reset the game to its initial state

The project should avoid external dependencies unless they are explicitly declared in CMakeLists.txt.
The project must compile and pass all tests using CMake and the provided tests/test_main.cpp.
"""