from typing import Final

desc: Final[str] = "Build Python project (Tank Battle game, pytest)."

idea: Final[str] = """
Generate a complete Python Tank Battle Game project.

All required files must be generated exactly as specified.
Do not rename, omit, or replace required files.
If your preferred project structure conflicts with the protocol, follow the protocol.

The project must be buildable and runnable in an automated evaluation environment.

The game should implement runtime-relevant Tank Battle core logic, such as:
- grid-based tank movement with position updates on a 2D map
- direction control for tanks, including Up, Down, Left, and Right
- map boundary handling, ensuring tanks and projectiles cannot move outside the valid game area
- obstacle or wall handling, including blocked cells that tanks cannot enter and projectiles cannot pass through
- tank state management, including tank id, position, direction, health, alive/destroyed state, and team or ownership information
- tank movement rules, including blocked movement when reaching map boundaries, walls, obstacles, or other alive tanks
- projectile firing logic, where tanks can create projectiles in their current facing direction
- projectile state management, including projectile position, direction, damage, active/inactive status, and owner id
- projectile movement logic, including step-based movement during game updates
- collision detection between tanks, projectiles, obstacles, walls, and map boundaries
- combat resolution, including applying projectile damage, reducing tank health, destroying tanks when health reaches zero, and deactivating projectiles after impact
- friendly-fire or self-hit handling with a clearly defined deterministic rule
- enemy tank or simple combat logic, including at least one non-player tank that can be placed on the map and participate in movement, firing, collision, and damage logic
- game state tracking, including running, victory, defeat, or draw states
- deterministic game update steps that advance projectiles, resolve collisions, update tank states, and check end conditions in a predictable order
- reusable public interfaces that allow tests to create tanks, move them, rotate them, fire projectiles, advance the game state, and inspect positions, health, projectile status, and victory conditions

The implementation should keep all core mechanics independent from graphics, real-time input, keyboard interaction, mouse input, random behavior, or terminal-based manual control.

Main.py should only provide a minimal runnable demonstration.
The core game logic should be implemented in reusable Python modules and classes so that tests can directly validate the runtime behavior.

The tests must:
- be fully automated
- require no manual interaction
- validate runtime-relevant core logic
- avoid GUI-dependent interaction whenever possible
- cover tank movement, direction changes, boundary blocking, obstacle blocking, projectile firing, projectile movement, projectile-wall collision, projectile-tank collision, health reduction, destroyed tank behavior, and game end conditions
- return exit code 0 on success and non-zero on failure
"""