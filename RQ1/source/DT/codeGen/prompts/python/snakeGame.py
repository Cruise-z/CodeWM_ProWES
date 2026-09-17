from typing import Final

desc: Final[str] = "Build Python project (Snake game, pytest)."

idea: Final[str] = """
Generate a complete Python Snake Game project.

All required files must be generated exactly as specified.
Do not rename, omit, or replace required files.
If your preferred project structure conflicts with the protocol, follow the protocol.

The project must be buildable and runnable in an automated evaluation environment.

The game should implement runtime-relevant Snake Game core logic, such as:
- grid-based snake movement with position updates on a 2D map
- direction control for the snake, including Up, Down, Left, and Right
- deterministic direction-change rules, including preventing invalid immediate reverse-direction movement when appropriate
- map boundary handling, ensuring the snake cannot move outside the valid game area
- snake body state management, including head position, body segments, current direction, alive/dead state, and pending growth state
- snake movement rules, including advancing the head, shifting body segments, preserving or removing the tail depending on growth state, and updating the full body position deterministically
- food state management, including food position, whether food is currently available, and deterministic placement or manually specified placement for testing
- food consumption logic, where the snake grows and score increases when the snake head reaches the food position
- collision detection between the snake head, map boundaries, food, and the snake's own body
- self-collision handling, including detecting when the snake head moves into its own body and marking the snake as dead
- scoring logic, including score increase after food consumption and score inspection through public interfaces
- game state tracking, including running, game-over, win, or completed states when applicable
- deterministic game update steps that apply direction changes, move the snake, resolve food consumption, update score and growth, check collisions, and update the game state in a predictable order
- reusable public interfaces that allow tests to create a game, inspect the snake body, change direction, advance the game state, place food, inspect score, check alive/dead status, and verify game-over conditions

The implementation should keep all core mechanics independent from graphics, real-time input, keyboard interaction, mouse input, random behavior, or terminal-based manual control.

Main.py should only provide a minimal runnable demonstration.
The core game logic should be implemented in reusable Python modules and classes so that tests can directly validate the runtime behavior.

The tests must:
- be fully automated
- require no manual interaction
- validate runtime-relevant core logic
- avoid GUI-dependent interaction whenever possible
- cover snake initialization, direction changes, invalid reverse-direction blocking, normal movement, boundary collision, food placement, food consumption, score increase, snake growth, self-collision, dead-snake behavior, and game end conditions
- return exit code 0 on success and non-zero on failure
"""