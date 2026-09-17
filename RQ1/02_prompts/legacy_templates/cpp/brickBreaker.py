from typing import Final

desc: Final[str] = "Build C++ project (Brick breaker game, CMake, C++17)."

idea: Final[str] = """
Generate a complete C++17 CMake Brick Breaker Game project.

All required files must be generated exactly as specified.
Do not rename, omit, or replace required files.
If your preferred project structure conflicts with the protocol, follow the protocol.

The project must be buildable and runnable in an automated evaluation environment.

The tests must:
- be fully automated
- require no manual interaction
- validate runtime-relevant core logic
- avoid GUI-dependent interaction whenever possible
- return exit code 0 on success and non-zero on failure
- NOT DEPEND ON GoogleTest, Catch2, doctest, or any external testing framework.
- tests/test_main.cpp must be implemented using only the C++17 standard library.
"""