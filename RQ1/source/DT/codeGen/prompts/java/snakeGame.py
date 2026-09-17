from typing import Final

# Short description; edit as needed.

desc: Final[str] = "Build Java project (Snake game, Maven, Java 11)."

idea: Final[str] = """
Generate a complete Java 11 Maven Snake Game project.

All required files must be generated exactly as specified.
Do not rename, omit, or replace required files.
If your preferred project structure conflicts with the protocol, follow the protocol.

The project must be buildable and runnable in an automated evaluation environment.

The game should implement a small but complete snake game system, including:

* a controllable snake
* food generation and consumption
* snake growth after eating food
* map boundaries
* collision detection with walls
* collision detection with the snake's own body
* score tracking
* game-over logic
* restart or reset logic when appropriate

The implementation should separate GUI-independent core logic from any optional UI code.
Core gameplay rules must be testable without launching a GUI window.

The game may include a simple Swing-based UI, but the UI must not be required for automated testing.
All core logic such as movement, food consumption, growth, scoring, and collision detection should be implemented in reusable classes independent of the GUI.

The tests must:

* be fully automated
* require no manual interaction
* validate runtime-relevant core logic
* avoid GUI-dependent interaction whenever possible
* return exit code 0 on success and non-zero on failure

The automated tests should cover important game logic such as:

* snake movement in different directions
* prevention of invalid reverse-direction movement when appropriate
* food consumption
* snake growth after eating food
* score updates
* wall collision and game-over detection
* self-collision and game-over detection
* reset or restart behavior when applicable

The project should avoid external dependencies unless they are declared in pom.xml.
The project must compile and pass all tests using mvn test.
"""
