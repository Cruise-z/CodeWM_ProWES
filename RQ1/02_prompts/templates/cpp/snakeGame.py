from typing import Final

desc: Final[str] = "Build C++ project (Snake game, CMake, C++17)."

idea: Final[str] = """
Generate a complete C++17 CMake Snake Game project.

All required files must be generated exactly as specified.
Do not rename, omit, or replace required files.
If your preferred project structure conflicts with the protocol, follow the protocol.

The project must be buildable and runnable in an automated evaluation environment.

The game should implement runtime-relevant Snake Game core logic, such as:

* snake movement
* direction control
* food generation
* food consumption
* snake growth after eating food
* score tracking
* map boundaries
* wall collision detection
* self-collision detection
* game-over state
* reset or restart logic when appropriate

The tests must:

* be fully automated
* require no manual interaction
* validate runtime-relevant core logic
* avoid GUI-dependent interaction whenever possible
* return exit code 0 on success and non-zero on failure
* NOT DEPEND ON GoogleTest, Catch2, doctest, or any external testing framework.
* tests/test_main.cpp must be implemented using only the C++17 standard library.

The automated tests should cover important game logic such as:

* snake movement in different directions
* prevention of invalid reverse-direction movement when appropriate
* food consumption
* snake growth after eating food
* score updates after eating food
* wall collision and game-over detection
* self-collision and game-over detection
* reset or restart behavior when applicable

The implementation should separate core game logic from presentation/input handling where possible,
so that the core logic can be tested without requiring graphics, keyboard input, terminal control, or real-time interaction.

The project should avoid external dependencies unless they are explicitly declared in CMakeLists.txt.
The project must compile and pass all tests using CMake and the provided tests/test_main.cpp.
"""
