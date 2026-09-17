from typing import Final

# Short description; edit as needed.

desc: Final[str] = "Build Java project (Flappy Bird game, Maven, Java 11)."

idea: Final[str] = """
Generate a complete Java 11 Maven Flappy Bird Game project.

All required files must be generated exactly as specified.
Do not rename, omit, or replace required files.
If your preferred project structure conflicts with the protocol, follow the protocol.

The project must be buildable and runnable in an automated evaluation environment.

The game should implement a small but complete Flappy Bird game system, including:

* a controllable bird
* bird vertical movement
* gravity simulation
* flap or jump behavior
* pipe generation
* pipe movement
* gaps between upper and lower pipes
* collision detection with pipes
* collision detection with map boundaries
* score tracking when the bird successfully passes pipes
* game-over logic
* restart or reset logic when appropriate

The implementation should separate GUI-independent core logic from any optional UI code.
Core gameplay rules must be testable without launching a GUI window.

The game may include a simple Swing-based UI, but the UI must not be required for automated testing.
All core logic such as bird movement, gravity, flap behavior, pipe movement, scoring, collision detection, and game-over handling should be implemented in reusable classes independent of the GUI.

The implementation should use deterministic update steps so that tests can reliably validate game behavior.
Pipe positions, bird movement, collision checks, score updates, and game-over state transitions should be predictable and testable without relying on real-time input, random behavior, keyboard interaction, or graphical rendering.

The game should provide reusable public interfaces that allow tests to:

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

The tests must:

* be fully automated
* require no manual interaction
* validate runtime-relevant core logic
* avoid GUI-dependent interaction whenever possible
* return exit code 0 on success and non-zero on failure

The automated tests should cover important game logic such as:

* initial bird position and game state
* gravity affecting bird movement
* flap behavior changing bird velocity or position
* deterministic game update steps
* pipe movement across the map
* pipe-gap configuration
* collision detection with upper and lower pipes
* collision detection with top and bottom boundaries
* score updates after the bird passes pipes
* game-over detection after collision
* prevention of normal updates after game over when appropriate
* reset or restart behavior when applicable

The project should avoid external dependencies unless they are declared in pom.xml.
The project must compile and pass all tests using mvn test.
"""
