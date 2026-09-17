from typing import Final

desc: Final[str] = "Build Python project (Flappy Bird game, pytest)."

idea: Final[str] = """
Generate a complete Python Flappy Bird Game project.

All required files must be generated exactly as specified.
Do not rename, omit, or replace required files.
If your preferred project structure conflicts with the protocol, follow the protocol.

The project must be buildable and runnable in an automated evaluation environment.

The game should implement runtime-relevant Flappy Bird Game core logic, such as:
- bird state management, including position, velocity, alive/dead state, and collision status
- vertical bird movement on a 2D game area
- gravity simulation that updates the bird velocity and position deterministically
- flap or jump behavior that changes the bird's vertical velocity in a predictable way
- map boundary handling, including top and bottom boundary collision detection
- pipe state management, including pipe position, width, gap position, gap size, active/inactive status, and whether the pipe has already been scored
- pipe movement logic, including step-based horizontal movement during game updates
- pipe generation or deterministic pipe placement for testing
- pipe gap handling, including upper and lower pipe collision regions
- collision detection between the bird, map boundaries, upper pipes, and lower pipes
- scoring logic, including score increase when the bird successfully passes a pipe
- game state tracking, including running, game-over, or completed states when applicable
- reset or restart logic that restores the bird, pipes, score, and game state to an initial condition
- deterministic game update steps that apply gravity, move the bird, move pipes, resolve collisions, update score, and update the game state in a predictable order
- reusable public interfaces that allow tests to create a game, inspect bird position and velocity, trigger a flap, advance the game state, add or configure pipes, inspect pipe positions, inspect score, check collision status, and verify game-over conditions

The implementation should keep all core mechanics independent from graphics, real-time input, keyboard interaction, mouse input, random behavior, or terminal-based manual control.

Main.py should only provide a minimal runnable demonstration.
The core game logic should be implemented in reusable Python modules and classes so that tests can directly validate the runtime behavior.

The tests must:
- be fully automated
- require no manual interaction
- validate runtime-relevant core logic
- avoid GUI-dependent interaction whenever possible
- cover bird initialization, gravity updates, flap behavior, deterministic movement, pipe placement, pipe movement, pipe gap handling, boundary collision, pipe collision, score increase after passing pipes, game-over behavior, reset behavior, and game end conditions
- return exit code 0 on success and non-zero on failure
"""