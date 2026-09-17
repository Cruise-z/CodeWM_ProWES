from typing import Final

desc: Final[str] = "Build Python project (Brick breaker game, pytest)."

idea: Final[str] = """
Generate a complete Python Brick Breaker Game project.

All required files must be generated exactly as specified.
Do not rename, omit, or replace required files.
If your preferred project structure conflicts with the protocol, follow the protocol.

The project must follow this interface protocol exactly:
- Build file: requirements.txt
- Runtime entry: Main.py
- Test target: tests/test_main.py
- Test executed via: pytest

The project must be buildable and runnable in an automated evaluation environment.

The tests must:
- be fully automated
- require no manual interaction
- validate runtime-relevant core logic
- avoid GUI-dependent interaction whenever possible
- return exit code 0 on success and non-zero on failure
"""