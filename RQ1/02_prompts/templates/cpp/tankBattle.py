from typing import Final

desc: Final[str] = "Build C++ project (Tank Battle game, CMake, C++17)."

idea: Final[str] = """
Generate a complete C++17 CMake Tank Battle Game project.

All required files must be generated exactly as specified.
Do not rename, omit, or replace required files.
If your preferred project structure conflicts with the protocol, follow the protocol.

The project must be buildable and runnable in an automated evaluation environment.

The game should implement runtime-relevant Tank Battle core logic, such as:
- tank movement
- direction control
- projectile firing
- projectile movement
- collision detection
- map boundaries
- obstacles or walls
- enemy tanks or simple combat logic
- health, hit, or destruction state

The tests must:
- be fully automated
- require no manual interaction
- validate runtime-relevant core logic
- avoid GUI-dependent interaction whenever possible
- return exit code 0 on success and non-zero on failure
- NOT DEPEND ON GoogleTest, Catch2, doctest, or any external testing framework.
- tests/test_main.cpp must be implemented using only the C++17 standard library.

The implementation should separate core game logic from presentation/input handling where possible,
so that the core logic can be tested without requiring graphics, keyboard input, or real-time interaction.
"""